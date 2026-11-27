#!/usr/bin/env python3
"""
GliHub 3.0 Phase 2 Verification & Pure-CPU Low-Precision Benchmark Suite.
Verifies:
  1. Pure-CPU INT8 latency (mean / P50 / P95 ms), FPS, and steady RSS memory (< 350 MB target)
  2. Composite EHS PPE detection (`yolo26n.int8.onnx` + `yolov5_helmet.int8.onnx`) on real industrial samples
  3. Unified 4-task no-NMS decode (`detect`, `pose`, `seg`, `obb`), Polygon ROI filter & Dynamic FPS throttling
  4. SQLite WAL offline ring-buffer store-and-forward (Center offline -> local persist -> Center online -> batch replay)
  5. SHA256-verified atomic OTA hot-reload (tamper rejection + valid hot swap)
"""
from __future__ import annotations

import asyncio
import json
import math
import statistics
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List

import cv2
import numpy as np
import psutil

from core.config_loader import ConfigManager
from core.pipeline import EdgePipelineService
from core.precision_runtime import OnnxYoloEngine, compute_sha256
from core.roi_filter import filter_detections_by_roi
from core.stream_reader import DynamicFpsController


class _MockCenterHandler(BaseHTTPRequestHandler):
    received_batches: List[Dict[str, Any]] = []
    received_tokens: List[str] = []

    def log_message(self, format: str, *args: Any) -> None:  # noqa: A003
        return

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers.get("Content-Length", "0"))
        raw = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        body = json.loads(raw or "{}")
        _MockCenterHandler.received_tokens.append(self.headers.get("X-Edge-Token", ""))

        if self.path == "/ehs/edge/alerts/batch":
            _MockCenterHandler.received_batches.append(body)
            uuids = [ev["alertUuid"] for ev in body.get("events", [])]
            resp = {"code": 200, "data": {"acceptedUuids": uuids, "acceptedCount": len(uuids)}}
        else:
            resp = {"code": 200, "data": {"ack": True, "nodeId": 101}}

        encoded = json.dumps(resp).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(encoded)))
        self.end_headers()
        self.wfile.write(encoded)


def verify_four_tasks_decode(engine: OnnxYoloEngine) -> Dict[str, Any]:
    """Verifies unified no-NMS decoder across detect, pose, seg, and obb tensor layouts."""
    names = {0: "person", 1: "chemical_drum"}
    # 1. detect: (1, 300, 6)
    det_t = np.zeros((1, 300, 6), dtype=np.float32)
    det_t[0, 0] = [100, 120, 260, 480, 0.91, 0]
    d_out = engine._decode_outputs(det_t, None, "detect", 0.35, 0.45, 1.0, 0.0, 0.0, 640, 640, 640, names)

    # 2. pose: (1, 300, 57) with horizontal fall aspect ratio
    pose_t = np.zeros((1, 300, 57), dtype=np.float32)
    pose_t[0, 0, :6] = [80, 320, 420, 490, 0.88, 0]
    for k in range(17):
        pose_t[0, 0, 6 + k * 3 : 6 + k * 3 + 3] = [120 + k * 12, 380, 0.92]
    p_out = engine._decode_outputs(pose_t, None, "pose", 0.35, 0.45, 1.0, 0.0, 0.0, 640, 640, 640, names)

    # 3. seg: (1, 300, 38) + proto (1, 32, 160, 160)
    seg_t = np.zeros((1, 300, 38), dtype=np.float32)
    seg_t[0, 0, :6] = [160, 160, 360, 360, 0.86, 1]
    seg_t[0, 0, 6:] = 0.5
    proto = np.ones((1, 32, 160, 160), dtype=np.float32) * 0.25
    s_out = engine._decode_outputs(seg_t, proto, "seg", 0.35, 0.45, 1.0, 0.0, 0.0, 640, 640, 640, names)

    # 4. obb: (1, 300, 7) -> [cx, cy, w, h, conf, cls, angle_rad]
    obb_t = np.zeros((1, 300, 7), dtype=np.float32)
    obb_t[0, 0] = [320, 240, 140, 70, 0.89, 1, math.radians(30.0)]
    o_out = engine._decode_outputs(obb_t, None, "obb", 0.35, 0.45, 1.0, 0.0, 0.0, 640, 640, 640, names)

    assert len(d_out) == 1 and d_out[0]["task_type"] == "detect"
    assert len(p_out) == 1 and len(p_out[0]["keypoints"]) == 17 and p_out[0].get("posture_alert") == "FALL_SUSPECTED"
    assert len(s_out) == 1 and s_out[0]["mask_area_ratio"] > 0.05
    assert len(o_out) == 1 and len(o_out[0]["obb_corners"]) == 4 and abs(o_out[0]["angle_deg"] - 30.0) < 0.2
    return {
        "detect_ok": True,
        "pose_17kpts_and_fall_ok": True,
        "seg_mask_area_ratio": s_out[0]["mask_area_ratio"],
        "obb_angle_deg": o_out[0]["angle_deg"],
    }


async def run_benchmark() -> Dict[str, Any]:
    edge_dir = Path(__file__).resolve().parent
    glihub_root = edge_dir.parent
    calib_dir = glihub_root / "data" / "calib_samples"

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        cfg_mgr = ConfigManager(edge_dir / "config.example.yaml")
        cfg_mgr.config.sqlite_path = str(tmp_path / "bench_outbox.db")
        cfg_mgr.config.center_base_url = "http://127.0.0.1:19999"  # Unreachable initially (offline mode)
        cfg_mgr.config.channels[0].silence_window_sec = 0

        pipeline = EdgePipelineService(cfg_mgr)
        proc = psutil.Process()

        sample_files = sorted([p for p in calib_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
        frames = [cv2.imread(str(p)) for p in sample_files[:8]]
        frames = [f for f in frames if f is not None]
        if not frames:
            frames = [np.random.randint(0, 255, (640, 640, 3), dtype=np.uint8)]

        # Warmup (5 iterations)
        for i in range(5):
            pipeline.primary_engine.infer(frames[i % len(frames)], task_type="detect")

        # 1. Pure-CPU Primary YOLO26n INT8 No-NMS Benchmark (40 frames)
        latencies_primary: List[float] = []
        for i in range(40):
            _, ms = pipeline.primary_engine.infer(frames[i % len(frames)], task_type="detect", conf_thres=0.35)
            latencies_primary.append(ms)

        mean_ms = statistics.mean(latencies_primary)
        p50_ms = statistics.median(latencies_primary)
        p95_ms = sorted(latencies_primary)[int(len(latencies_primary) * 0.95)]
        pure_fps = 1000.0 / mean_ms

        # 2. Composite EHS PPE Pipeline Benchmark (YOLO26n INT8 + Custom YOLOv5 Helmet INT8)
        zidane_candidates = [p for p in sample_files if "zidane" in p.name.lower()]
        helmet_candidates = [p for p in sample_files if "bikeshelmets0" in p.name.lower()]

        no_helmet_res = None
        if zidane_candidates:
            z_img = cv2.imread(str(zidane_candidates[0]))
            no_helmet_res = pipeline.process_frame(z_img, enqueue_alert=True, force_enqueue=True)

        with_helmet_res = None
        if helmet_candidates:
            h_img = cv2.imread(str(helmet_candidates[0]))
            with_helmet_res = pipeline.process_frame(h_img, enqueue_alert=False)

        # 3. Unified 4-task decode + ROI + Dynamic FPS check
        four_task_report = verify_four_tasks_decode(pipeline.primary_engine)
        kept, dropped = filter_detections_by_roi(
            [
                {"class_name": "person", "bbox": [100, 100, 200, 300]},
                {"class_name": "person", "bbox": [550, 500, 620, 620]},
            ],
            [[0.05, 0.05], [0.5, 0.05], [0.5, 0.6], [0.05, 0.6]],
            640,
            640,
        )
        assert len(kept) == 1 and dropped == 1

        dyn_fps = DynamicFpsController(enabled=True, idle_fps=0.5, active_fps=10.0)
        static_frame = frames[0]
        for step in range(10):
            dyn_fps.should_process(static_frame, now_ts=100.0 + step * 0.1)

        # 4. Offline Store-and-Forward Queue Verification
        # Attempt flush while Center (:19999) is offline -> stays PENDING with retry_count=1
        offline_flush = await pipeline.flush_outbox_once(force=True)
        pending_while_offline = pipeline.queue.stats()["pending"]
        assert pending_while_offline >= 1 and not offline_flush["center_online"]

        # Start Mock Center HTTP Server on ephemeral port & recover online!
        server = HTTPServer(("127.0.0.1", 0), _MockCenterHandler)
        mock_port = server.server_address[1]
        srv_thread = threading.Thread(target=server.serve_forever, daemon=True)
        srv_thread.start()
        try:
            cfg_mgr.config.center_base_url = f"http://127.0.0.1:{mock_port}"
            online_flush = await pipeline.flush_outbox_once(force=True)
            after_stats = pipeline.queue.stats()
            assert online_flush["center_online"] is True
            assert online_flush["uploaded"] == pending_while_offline
            assert after_stats["pending"] == 0 and after_stats["synced"] == pending_while_offline
        finally:
            server.shutdown()
            server.server_close()

        # 5. SHA256 OTA Tamper Rejection & Valid Hot-Reload Verification
        src_model = pipeline.primary_engine.model_path
        valid_sha = compute_sha256(src_model)
        tamper_blocked = False
        try:
            await pipeline.ota.apply_ota(
                download_url=str(src_model),
                target_filename="ota_test_yolo26n.int8.onnx",
                expected_sha256="0" * 64,
            )
        except ValueError:
            tamper_blocked = True
        assert tamper_blocked, "OTA updater must reject mismatched SHA256!"

        ota_ok = await pipeline.ota.apply_ota(
            download_url=str(src_model),
            target_filename=src_model.name,
            expected_sha256=valid_sha,
        )

        rss_mb = round(proc.memory_info().rss / (1024.0 * 1024.0), 2)
        report = {
            "runtime": pipeline.primary_engine.runtime_info(),
            "ppe_auxiliary_model": pipeline.helmet_engine.model_path.name
            if (pipeline.helmet_engine and pipeline.helmet_engine.session)
            else None,
            "benchmark_yolo26n_int8": {
                "frames": 40,
                "mean_latency_ms": round(mean_ms, 2),
                "p50_latency_ms": round(p50_ms, 2),
                "p95_latency_ms": round(p95_ms, 2),
                "throughput_fps": round(pure_fps, 2),
                "rss_memory_mb": rss_mb,
                "under_350mb_budget": rss_mb < 350.0,
            },
            "composite_ppe_verification": {
                "unprotected_sample_violations": no_helmet_res["violations_count"] if no_helmet_res else None,
                "compliant_sample_violations": with_helmet_res["violations_count"] if with_helmet_res else None,
                "composite_latency_ms": no_helmet_res["latency_ms"] if no_helmet_res else None,
            },
            "four_tasks_and_roi": {
                **four_task_report,
                "roi_kept": len(kept),
                "roi_filtered_out": dropped,
                "dynamic_fps_static_skipped_of_10": dyn_fps.frames_skipped,
            },
            "offline_store_and_forward": {
                "queued_while_offline": pending_while_offline,
                "replayed_on_reconnect": online_flush["uploaded"],
                "remaining_pending": after_stats["pending"],
                "edge_token_verified": cfg_mgr.config.edge_token in _MockCenterHandler.received_tokens,
            },
            "ota_sha256_security": {
                "tampered_sha256_rejected": tamper_blocked,
                "valid_hot_reload_status": ota_ok["status"],
            },
        }
        print(json.dumps(report, indent=2, ensure_ascii=False))
        return report


if __name__ == "__main__":
    asyncio.run(run_benchmark())
