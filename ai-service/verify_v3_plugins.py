#!/usr/bin/env python3
"""
GliHub 3.0 Phase 3 Verification Suite:
Tests both 0-Plugin Safe Degradation Mode AND `cpu-int8` 7-Plugin Modular Mode.
"""
from __future__ import annotations

import json
from pathlib import Path
import psutil
from fastapi.testclient import TestClient

from config import settings
from core.plugin_registry import plugin_registry
from main import app


def run_zero_plugin_check() -> dict:
    """Verifies that disabling all 7 plugins never crashes any core API."""
    settings.disable_all_plugins = True
    try:
        with TestClient(app) as client:
            h = client.get("/api/v1/health")
            assert h.status_code == 200 and h.json()["plugins_active_count"] == 0

            sample_img = "yolov5target-main/data/images/zidane.jpg"
            vis = client.post(
                "/api/v1/vision/analyze",
                json={"image_path": sample_img, "model_code": "yolov5_helmet_local", "enable_vlm": True},
            )
            assert vis.status_code == 200
            vis_body = vis.json()
            assert vis_body["vision"]["adapter_type"] == "zero-plugin-safe-mode"
            assert vis_body["vision"]["fallback_used"] is True

            rep = client.post(
                "/api/v1/agents/eval-report",
                json={
                    "place_type": "production",
                    "area_name": "一车间",
                    "eval_summary": {"lec": {"d": 126, "grade": "二级", "levelText": "高度危险"}},
                },
            )
            assert rep.status_code == 200 and "126" in rep.json()["report_markdown"]
            return {"zero_plugin_all_endpoints_200": True, "zero_plugin_adapter": vis_body["vision"]["adapter_type"]}
    finally:
        settings.disable_all_plugins = False


def run_cpu_int8_plugins_check() -> dict:
    proc = psutil.Process()
    with TestClient(app) as client:
        plugins_resp = client.get("/api/v1/plugins").json()
        by_id = {p["plugin_id"]: p for p in plugins_resp["plugins"]}
        assert len(by_id) == 7, f"Expected 7 plugins, got {len(by_id)}"
        assert by_id["mod-rfdetr"]["status"] in ("NOT_INSTALLED", "GPU_REQUIRED")

        # 1. mod-yolov5 INT8 coupled violation check on zidane.jpg
        v5_viol = client.post(
            "/api/v1/vision/analyze",
            json={
                "image_path": "yolov5target-main/data/images/zidane.jpg",
                "model_code": "yolov5_helmet_local",
                "enable_vlm": True,
                "place_type": "production",
                "area_name": "甲类装置区",
            },
        ).json()
        assert v5_viol["vision"]["has_violation"] is True
        assert v5_viol["vlm_review"]["is_real_hazard"] is True
        assert len(v5_viol["cited_laws"]) >= 1

        # 2. Compliant rectification recheck on BikesHelmets0.png
        recheck = client.post(
            "/api/v1/vision/recheck",
            json={
                "after_image_path": "yolov5target-main/data/images/archive/images/BikesHelmets0.png",
                "hazard_title": "未规范佩戴安全帽违章",
                "model_code": "yolov5_helmet_local",
            },
        ).json()
        assert recheck["passed"] is True and len(recheck["remaining_violations"]) == 0

        # 3. mod-yolo26 native no-NMS INT8
        y26 = client.post(
            "/api/v1/vision/analyze",
            json={
                "image_path": "yolov5target-main/data/images/bus.jpg",
                "model_code": "yolo26n_rt",
                "enable_vlm": False,
            },
        ).json()
        assert y26["vision"]["plugin_id"] == "mod-yolo26"
        assert len(y26["vision"]["detections"]) >= 3

        # 4. mod-rfdetr on CPU gracefully falls back to mod-yolo26
        rfd = client.post(
            "/api/v1/vision/analyze",
            json={
                "image_path": "yolov5target-main/data/images/bus.jpg",
                "model_code": "rfdetr_precision",
                "enable_vlm": False,
            },
        ).json()
        assert rfd["vision"]["fallback_used"] is True and rfd["vision"]["plugin_id"] == "mod-yolo26"

        # 5. mod-yoloe open-vocabulary Chinese prompt inspection
        ov = client.post(
            "/api/v1/vision/open-vocab",
            json={
                "image_path": "yolov5target-main/data/images/zidane.jpg",
                "prompts": ["未佩戴安全帽", "违规使用手机"],
                "enable_vlm": True,
            },
        ).json()
        assert ov["vision"]["plugin_id"] == "mod-yoloe" and ov["vision"]["has_violation"] is True

        # 6. Hot-toggle plugin off and back on
        t_off = client.post("/api/v1/plugins/mod-yolo26/toggle", json={"enabled": False}).json()
        assert t_off["plugin"]["status"] == "DISABLED"
        t_on = client.post("/api/v1/plugins/mod-yolo26/toggle", json={"enabled": True}).json()
        assert t_on["plugin"]["status"] == "ACTIVE"

        # 7. mod-ocr clause parsing test
        tmp_doc = Path(settings.output_dir) / "sample_sds.txt"
        tmp_doc.write_text(
            "第一条 甲醇储罐区必须设置固定式可燃气体检测报警器。\n第二条 进入甲类火灾危险区域必须佩戴防静电安全帽。",
            encoding="utf-8",
        )
        ocr_res = client.post(
            "/api/v1/ocr/parse",
            data={"file_path": str(tmp_doc), "doc_title": "甲醇安全规程", "ingest_to_kb": "false"},
        ).json()
        assert ocr_res["chunk_count"] >= 2

        rss_mb = round(proc.memory_info().rss / (1024.0 * 1024.0), 2)
        return {
            "plugins_statuses": {pid: p["status"] for pid, p in by_id.items()},
            "yolov5_int8_ms": v5_viol["vision"]["inference_ms"],
            "yolov5_recheck_passed": recheck["passed"],
            "yolo26_int8_ms": y26["vision"]["inference_ms"],
            "rfdetr_cpu_graceful_fallback_to": rfd["vision"]["plugin_id"],
            "yoloe_open_vocab_detections": len(ov["vision"]["detections"]),
            "ocr_parsed_chunks": ocr_res["chunk_count"],
            "rss_memory_mb": rss_mb,
            "under_450mb_budget": rss_mb < 450.0,
        }


if __name__ == "__main__":
    zero_rep = run_zero_plugin_check()
    int8_rep = run_cpu_int8_plugins_check()
    # Clean temporary state override created during toggle test
    plugin_registry.state_path.unlink(missing_ok=True)
    print(json.dumps({"zero_plugin_mode": zero_rep, "cpu_int8_mode": int8_rep}, indent=2, ensure_ascii=False))
