from __future__ import annotations

import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional


class OfflineAlertQueue:
    """
    Zero-dependency SQLite WAL ring-buffer outbox for store-and-forward edge alerts.
    Survives power loss & network outages; automatically evicts oldest records when
    `max_records` is exceeded so embedded eMMC/SD storage never fills up.
    """

    def __init__(self, db_path: Path, max_records: int = 5000) -> None:
        self.db_path = Path(db_path).resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.max_records = max(100, int(max_records))
        self._lock = threading.RLock()
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), timeout=10.0, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        return conn

    def _init_db(self) -> None:
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS edge_alert_outbox (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    alert_uuid TEXT NOT NULL UNIQUE,
                    channel_code TEXT NOT NULL,
                    dept_id INTEGER NOT NULL DEFAULT 103,
                    place_type TEXT NOT NULL DEFAULT 'PRODUCTION',
                    hazard_id INTEGER,
                    task_type TEXT NOT NULL DEFAULT 'detect',
                    model_name TEXT NOT NULL,
                    captured_at TEXT NOT NULL,
                    detections_json TEXT NOT NULL,
                    crop_b64 TEXT,
                    thumb_b64 TEXT,
                    status TEXT NOT NULL DEFAULT 'PENDING',
                    retry_count INTEGER NOT NULL DEFAULT 0,
                    next_retry_ts REAL NOT NULL DEFAULT 0,
                    last_error TEXT,
                    created_ts REAL NOT NULL
                );
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_outbox_status_retry ON edge_alert_outbox(status, next_retry_ts, id);"
            )
            conn.commit()

    def enqueue(
        self,
        *,
        channel_code: str,
        dept_id: int,
        place_type: str,
        hazard_id: Optional[int],
        task_type: str,
        model_name: str,
        captured_at: str,
        detections: List[Dict[str, Any]],
        crop_b64: str = "",
        thumb_b64: str = "",
        alert_uuid: Optional[str] = None,
    ) -> str:
        uid = alert_uuid or f"edge-{uuid.uuid4().hex[:20]}"
        now = time.time()
        with self._lock, self._connect() as conn:
            conn.execute(
                """
                INSERT OR IGNORE INTO edge_alert_outbox (
                    alert_uuid, channel_code, dept_id, place_type, hazard_id,
                    task_type, model_name, captured_at, detections_json,
                    crop_b64, thumb_b64, status, retry_count, next_retry_ts, created_ts
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'PENDING', 0, 0, ?)
                """,
                (
                    uid,
                    channel_code,
                    dept_id,
                    place_type,
                    hazard_id,
                    task_type,
                    model_name,
                    captured_at,
                    json.dumps(
                        detections,
                        ensure_ascii=False,
                        default=lambda o: float(o) if hasattr(o, "__float__") else str(o),
                    ),
                    crop_b64,
                    thumb_b64,
                    now,
                ),
            )
            self._enforce_ring_cap(conn)
            conn.commit()
        return uid

    def _enforce_ring_cap(self, conn: sqlite3.Connection) -> None:
        row = conn.execute("SELECT COUNT(*) AS cnt FROM edge_alert_outbox").fetchone()
        total = int(row["cnt"]) if row else 0
        overflow = total - self.max_records
        if overflow <= 0:
            return
        # Evict oldest SYNCED records first; if still overflowing, evict oldest overall
        conn.execute(
            """
            DELETE FROM edge_alert_outbox WHERE id IN (
                SELECT id FROM edge_alert_outbox
                ORDER BY CASE WHEN status = 'SYNCED' THEN 0 ELSE 1 END ASC, id ASC
                LIMIT ?
            )
            """,
            (overflow,),
        )

    def fetch_ready_batch(self, limit: int = 10, ignore_backoff: bool = False) -> List[Dict[str, Any]]:
        now = time.time()
        with self._lock, self._connect() as conn:
            if ignore_backoff:
                rows = conn.execute(
                    """
                    SELECT * FROM edge_alert_outbox
                    WHERE status = 'PENDING'
                    ORDER BY id ASC LIMIT ?
                    """,
                    (limit,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT * FROM edge_alert_outbox
                    WHERE status = 'PENDING' AND next_retry_ts <= ?
                    ORDER BY id ASC LIMIT ?
                    """,
                    (now, limit),
                ).fetchall()

        batch: List[Dict[str, Any]] = []
        for r in rows:
            batch.append(
                {
                    "id": r["id"],
                    "alertUuid": r["alert_uuid"],
                    "channelCode": r["channel_code"],
                    "deptId": r["dept_id"],
                    "placeType": r["place_type"],
                    "hazardId": r["hazard_id"],
                    "taskType": r["task_type"],
                    "modelName": r["model_name"],
                    "capturedAt": r["captured_at"],
                    "detections": json.loads(r["detections_json"] or "[]"),
                    "cropImageB64": r["crop_b64"] or "",
                    "annotatedThumbB64": r["thumb_b64"] or "",
                    "retryCount": r["retry_count"],
                }
            )
        return batch

    def mark_synced(self, alert_uuids: List[str]) -> int:
        if not alert_uuids:
            return 0
        placeholders = ",".join("?" for _ in alert_uuids)
        with self._lock, self._connect() as conn:
            cur = conn.execute(
                f"UPDATE edge_alert_outbox SET status = 'SYNCED', last_error = NULL WHERE alert_uuid IN ({placeholders})",
                alert_uuids,
            )
            conn.commit()
            return cur.rowcount

    def mark_retry(self, alert_uuids: List[str], error_msg: str) -> None:
        if not alert_uuids:
            return
        now = time.time()
        with self._lock, self._connect() as conn:
            for uid in alert_uuids:
                row = conn.execute(
                    "SELECT retry_count FROM edge_alert_outbox WHERE alert_uuid = ?", (uid,)
                ).fetchone()
                rc = (int(row["retry_count"]) + 1) if row else 1
                backoff = min(120.0, 2.0 ** min(rc, 7))
                conn.execute(
                    """
                    UPDATE edge_alert_outbox
                    SET retry_count = ?, next_retry_ts = ?, last_error = ?
                    WHERE alert_uuid = ?
                    """,
                    (rc, now + backoff, error_msg[:300], uid),
                )
            conn.commit()

    def stats(self) -> Dict[str, Any]:
        with self._lock, self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM edge_alert_outbox GROUP BY status"
            ).fetchall()
            counts = {"PENDING": 0, "SYNCED": 0, "FAILED": 0}
            for r in rows:
                counts[str(r["status"])] = int(r["cnt"])
            recent = conn.execute(
                """
                SELECT alert_uuid, channel_code, task_type, model_name, captured_at, status, retry_count, last_error
                FROM edge_alert_outbox ORDER BY id DESC LIMIT 15
                """
            ).fetchall()
        return {
            "pending": counts["PENDING"],
            "synced": counts["SYNCED"],
            "failed": counts["FAILED"],
            "total": sum(counts.values()),
            "max_records": self.max_records,
            "db_path": str(self.db_path),
            "recent": [dict(r) for r in recent],
        }
