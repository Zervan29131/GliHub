from __future__ import annotations

import asyncio
import base64
import collections
from datetime import datetime, timezone
from pathlib import Path
import time
from typing import Any, Deque, Dict, List, Optional, Tuple

import cv2
import numpy as np
import psutil

from core.config_loader import ChannelConfig, ConfigManager
from core.precision_runtime import OnnxYoloEngine
from core.roi_filter import couple_person_and_helmet, filter_detections_by_roi, normalize_polygon
from sync.cloud_client import CloudSyncClient
from sync.offline_queue import OfflineAlertQueue
from sync.ota_updater import OtaModelUpdater

SKELETON_EDGES = [
    (5, 7), (7, 9), (6, 8), (8, 10), (5, 6),
    (5, 11), (6, 12), (11, 12), (11, 13), (13, 15), (12, 14), (14, 16),
]


def encode_jpg_b64(img_bgr: np.ndarray, max_side: int = 640, quality: int = 80) -> str:
    if img_bgr is None or img_bgr.size == 0:
        return ""
    h, w = img_bgr.shape[:2]
    scale = min(1.0, float(max_side) / float(max(h, w, 1)))
    if scale < 1.0:
        img_bgr = cv2.resize(img_bgr, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)
    ok, buf = cv2.imencode(".jpg", img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    if not ok:
        return ""
    return base64.b64encode(buf.tobytes()).decode("ascii")


def render_annotated_frame(
    img_bgr: np.ndarray,
    detections: List[Dict[str, Any]],
    roi_polygon: Optional[List[List[float]]] = None,
) -> np.ndarray:
    canvas = img_bgr.copy()
    h, w = canvas.shape[:2]

    if roi_polygon and len(roi_polygon) >= 3:
        pts = np.array(normalize_polygon(roi_polygon, w, h), dtype=np.int32).reshape((-1, 1, 2))
        overlay = canvas.copy()
        cv2.fillPoly(overlay, [pts], (255, 190, 0))
        cv2.addWeighted(overlay, 0.08, canvas, 0.92, 0, canvas)
        cv2.polylines(canvas, [pts], isClosed=True, color=(255, 210, 0), thickness=2)

    for det in detections:
        is_viol = bool(det.get("is_violation", det.get("class_name") in ("no_helmet", "fire", "smoke")))
        color = (48, 59, 255) if is_viol else (129, 185, 16)
        bbox = [int(round(v)) for v in det.get("bbox", [0, 0, 0, 0])]
        x1, y1, x2, y2 = bbox

        if det.get("obb_corners"):
            obb_pts = np.array(det["obb_corners"], dtype=np.int32).reshape((-1, 1, 2))
            cv2.polylines(canvas, [obb_pts], True, (0, 215, 255), 2)
        else:
            cv2.rectangle(canvas, (x1, y1), (x2, y2), color, 2)

        if det.get("keypoints"):
            kpts = det["keypoints"]
            for a, b in SKELETON_EDGES:
                if a < len(kpts) and b < len(kpts) and kpts[a][2] > 0.3 and kpts[b][2] > 0.3:
                    cv2.line(
                        canvas,
                        (int(kpts[a][0]), int(kpts[a][1])),
                        (int(kpts[b][0]), int(kpts[b][1])),
                        (255, 180, 0),
                        2,
                    )
            for kx, ky, kc in kpts:
                if kc > 0.3:
                    cv2.circle(canvas, (int(kx), int(ky)), 3, (0, 255, 255), -1)

        tag = f"{det.get('class_name', 'obj')} {float(det.get('confidence', 0.0)):.2f}"
        if det.get("mask_area_ratio") is not None:
            tag += f" mask:{det['mask_area_ratio']*100:.1f}%"
        (tw, th), _ = cv2.getTextSize(tag, cv2.FONT_HERSHEY_SIMPLEX, 0.52, 1)
        ty = max(th + 6, y1)
        cv2.rectangle(canvas, (x1, ty - th - 6), (x1 + tw + 8, ty), color, -1)
        cv2.putText(
            canvas, tag, (x1 + 4, ty - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (255, 255, 255), 1, cv2.LINE_AA
        )

    return canvas


class EdgePipelineService:
    """Central coordinator inside `edge-yolo26/` uniting inference, ROI, SQLite outbox, and Cloud sync."""

    def __init__(self, cfg_mgr: ConfigManager) -> None:
        self.cfg_mgr = cfg_mgr
        cfg = cfg_mgr.config

        primary_path = cfg_mgr.resolve_path(cfg.primary_model_path)
        helmet_path = cfg_mgr.resolve_path(cfg.ppe_helmet_model_path)

        self.primary_engine = OnnxYoloEngine(
            model_path=primary_path,
            precision_mode=cfg.precision_mode,
            imgsz=cfg.imgsz,
            cpu_threads=cfg.cpu_threads,
        )
        self.helmet_engine: Optional[OnnxYoloEngine] = None
        if helmet_path.exists():
            self.helmet_engine = OnnxYoloEngine(
                model_path=helmet_path,
                precision_mode=cfg.precision_mode,
                imgsz=cfg.imgsz,
                cpu_threads=cfg.cpu_threads,
                default_names={0: "With Helmet"},
            )

        self.queue = OfflineAlertQueue(
            db_path=cfg_mgr.resolve_path(cfg.sqlite_path),
            max_records=cfg.max_queue_records,
        )
        self.cloud = CloudSyncClient(cfg_mgr)
        self.ota = OtaModelUpdater(
            models_dir=cfg_mgr.resolve_path(cfg.models_dir),
            engine=self.primary_engine,
            edge_token=cfg.edge_token,
        )

        self._silence_tracker: Dict[str, float] = {}
        self._latency_window: Deque[float] = collections.deque(maxlen=60)
        self._fps_window: Deque[float] = collections.deque(maxlen=60)
        self._process = psutil.Process()
        self._bg_tasks: List[asyncio.Task] = []
        self._stop_event = asyncio.Event()

    def process_frame(
        self,
        img_bgr: np.ndarray,
        channel: Optional[ChannelConfig] = None,
        task_override: Optional[str] = None,
        conf_override: Optional[float] = None,
        enqueue_alert: bool = True,
        force_enqueue: bool = False,
    ) -> Dict[str, Any]:
        ch = channel or self.cfg_mgr.config.channels[0]
        task_type = (task_override or ch.task_type or "detect").lower()
        conf_thres = float(conf_override if conf_override is not None else ch.conf_threshold)

        t_start = time.perf_counter()
        raw_dets, primary_ms = self.primary_engine.infer(
            img_bgr, task_type=task_type, conf_thres=conf_thres, iou_thres=self.cfg_mgr.config.iou_threshold
        )

        helmet_ms = 0.0
        merged_dets = raw_dets
        if task_type == "detect" and self.helmet_engine is not None and self.helmet_engine.session is not None:
            helmet_dets, helmet_ms = self.helmet_engine.infer(
                img_bgr, task_type="detect", conf_thres=max(0.28, conf_thres), iou_thres=0.45
            )
            if any(d.get("class_name") == "person" for d in raw_dets) or helmet_dets:
                merged_dets = couple_person_and_helmet(raw_dets, helmet_dets)

        h, w = img_bgr.shape[:2]
        roi_dets, roi_dropped = filter_detections_by_roi(merged_dets, ch.roi_polygon, w, h)

        total_ms = (time.perf_counter() - t_start) * 1000.0
        self._latency_window.append(total_ms)
        if total_ms > 0:
            self._fps_window.append(1000.0 / total_ms)

        violations = [
            d
            for d in roi_dets
            if d.get("is_violation")
            or d.get("class_name") in ("no_helmet", "fire", "smoke", "fall_risk")
        ]

        annotated = render_annotated_frame(img_bgr, roi_dets, ch.roi_polygon)
        thumb_b64 = encode_jpg_b64(annotated, max_side=640, quality=80)

        queued_uuid: Optional[str] = None
        target_events = violations if violations else (roi_dets if force_enqueue else [])
        if enqueue_alert and target_events:
            dedup_key = f"{ch.channel_code}:{target_events[0].get('class_name', 'event')}"
            now_mono = time.monotonic()
            last_ts = self._silence_tracker.get(dedup_key, 0.0)
            if force_enqueue or (now_mono - last_ts) >= ch.silence_window_sec:
                self._silence_tracker[dedup_key] = now_mono
                b0 = [int(round(v)) for v in target_events[0].get("bbox", [0, 0, w, h])]
                pad = 24
                cx1, cy1 = max(0, b0[0] - pad), max(0, b0[1] - pad)
                cx2, cy2 = min(w, b0[2] + pad), min(h, b0[3] + pad)
                crop_img = img_bgr[cy1:cy2, cx1:cx2] if (cx2 > cx1 and cy2 > cy1) else img_bgr
                crop_b64 = encode_jpg_b64(crop_img, max_side=416, quality=82)
                captured_iso = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
                model_label = self.primary_engine.model_path.name
                if self.helmet_engine and self.helmet_engine.session is not None and task_type == "detect":
                    model_label = f"{model_label}+{self.helmet_engine.model_path.name}"

                queued_uuid = self.queue.enqueue(
                    channel_code=ch.channel_code,
                    dept_id=ch.dept_id,
                    place_type=ch.place_type,
                    hazard_id=ch.hazard_id,
                    task_type=task_type,
                    model_name=model_label,
                    captured_at=captured_iso,
                    detections=target_events,
                    crop_b64=crop_b64,
                    thumb_b64=thumb_b64,
                )

        return {
            "channel_code": ch.channel_code,
            "task_type": task_type,
            "latency_ms": round(total_ms, 2),
            "primary_ms": round(primary_ms, 2),
            "helmet_ms": round(helmet_ms, 2),
            "detections": roi_dets,
            "violations_count": len(violations),
            "roi_filtered_out": roi_dropped,
            "queued_alert_uuid": queued_uuid,
            "annotated_b64": thumb_b64,
        }

    async def flush_outbox_once(self, force: bool = False) -> Dict[str, Any]:
        batch = self.queue.fetch_ready_batch(
            limit=self.cfg_mgr.config.batch_upload_size, ignore_backoff=force
        )
        if not batch:
            return {"uploaded": 0, "pending": self.queue.stats()["pending"], "center_online": self.cloud.center_online}

        ok, accepted_uuids, err = await self.cloud.upload_alerts_batch(batch)
        if ok:
            synced_cnt = self.queue.mark_synced(accepted_uuids)
            return {
                "uploaded": synced_cnt,
                "pending": self.queue.stats()["pending"],
                "center_online": True,
            }
        self.queue.mark_retry([item["alertUuid"] for item in batch], err)
        return {
            "uploaded": 0,
            "pending": self.queue.stats()["pending"],
            "center_online": False,
            "error": err,
        }

    def health_snapshot(self) -> Dict[str, Any]:
        rss_mb = round(self._process.memory_info().rss / (1024.0 * 1024.0), 2)
        avg_ms = round(sum(self._latency_window) / len(self._latency_window), 2) if self._latency_window else 0.0
        avg_fps = round(sum(self._fps_window) / len(self._fps_window), 2) if self._fps_window else 0.0
        q_stats = self.queue.stats()
        rt = self.primary_engine.runtime_info()
        return {
            "status": "UP",
            "service": "glihub-edge-yolo26",
            "version": "3.0.0",
            "node_code": self.cfg_mgr.config.node_code,
            "node_name": self.cfg_mgr.config.node_name,
            "config_version": self.cfg_mgr.config.config_version,
            "center_online": self.cloud.center_online,
            "center_url": self.cfg_mgr.config.center_base_url,
            "last_sync_error": self.cloud.last_sync_error,
            "metrics": {
                "rss_memory_mb": rss_mb,
                "cpu_percent": round(psutil.cpu_percent(interval=None), 1),
                "avg_latency_ms": avg_ms,
                "avg_infer_fps": avg_fps,
            },
            "runtime": rt,
            "ppe_auxiliary_loaded": bool(self.helmet_engine and self.helmet_engine.session is not None),
            "ppe_model_file": self.helmet_engine.model_path.name if (self.helmet_engine and self.helmet_engine.session) else None,
            "outbox": {
                "pending": q_stats["pending"],
                "synced": q_stats["synced"],
                "total": q_stats["total"],
                "max_records": q_stats["max_records"],
            },
        }

    async def start_background_loops(self) -> None:
        self._stop_event.clear()
        await self.cloud.register(self.primary_engine.runtime_info())
        self._bg_tasks = [
            asyncio.create_task(self._heartbeat_loop()),
            asyncio.create_task(self._flush_loop()),
        ]

    async def stop_background_loops(self) -> None:
        self._stop_event.set()
        for t in self._bg_tasks:
            t.cancel()
        self._bg_tasks.clear()

    async def _heartbeat_loop(self) -> None:
        while not self._stop_event.is_set():
            snap = self.health_snapshot()
            resp = await self.cloud.heartbeat(
                {
                    "nodeCode": snap["node_code"],
                    "fps": snap["metrics"]["avg_infer_fps"],
                    "cpuPercent": snap["metrics"]["cpu_percent"],
                    "memMb": snap["metrics"]["rss_memory_mb"],
                    "queuePendingCount": snap["outbox"]["pending"],
                    "activeModelCode": snap["runtime"]["model_file"],
                    "activeModelSha256": snap["runtime"]["model_sha256"],
                    "configVersion": snap["config_version"],
                }
            )
            if isinstance(resp, dict):
                desired_ver = int(resp.get("desiredConfigVersion") or 0)
                if desired_ver > self.cfg_mgr.config.config_version:
                    remote_cfg = await self.cloud.fetch_remote_config()
                    if remote_cfg:
                        self.cfg_mgr.apply_remote_config(remote_cfg)
                ota_cmd = resp.get("otaCommand")
                if isinstance(ota_cmd, dict) and ota_cmd.get("downloadUrl") and ota_cmd.get("targetModelFile"):
                    try:
                        await self.ota.apply_ota(
                            download_url=ota_cmd["downloadUrl"],
                            target_filename=ota_cmd["targetModelFile"],
                            expected_sha256=ota_cmd.get("sha256Hex"),
                        )
                    except Exception:
                        pass
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=float(self.cfg_mgr.config.heartbeat_interval_sec)
                )
            except asyncio.TimeoutError:
                pass

    async def _flush_loop(self) -> None:
        while not self._stop_event.is_set():
            await self.flush_outbox_once(force=False)
            try:
                await asyncio.wait_for(
                    self._stop_event.wait(), timeout=float(self.cfg_mgr.config.flush_interval_sec)
                )
            except asyncio.TimeoutError:
                pass
