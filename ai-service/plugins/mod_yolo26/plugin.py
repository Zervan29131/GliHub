from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from adapters.base import DetectionBox, VisionInferenceOutput, render_detections, translate_label
from config import settings
from core.plugin_registry import BaseAiPlugin
from core.precision import LowPrecisionOnnxRunner, precision_manager


class Yolo26Plugin(BaseAiPlugin):
    """
    Plugin 2 (`mod-yolo26`):
    Ultralytics YOLO26 native end-to-end no-NMS ONNX INT8 / FP16 detector.
    """

    def __init__(self, manifest: Dict[str, Any]) -> None:
        super().__init__(manifest)
        self._runner: Optional[LowPrecisionOnnxRunner] = None
        self._helmet_aux: Optional[LowPrecisionOnnxRunner] = None

    def _ensure_loaded(self) -> None:
        if self._runner is None:
            m_path = precision_manager.resolve_onnx_model_file("yolo26n")
            if m_path and m_path.exists():
                self._runner = LowPrecisionOnnxRunner(m_path)
        if self._helmet_aux is None:
            h_path = precision_manager.resolve_onnx_model_file("yolov5_helmet")
            if h_path and h_path.exists():
                self._helmet_aux = LowPrecisionOnnxRunner(h_path, default_names={0: "With Helmet"})

    def check_readiness(self) -> tuple[bool, str]:
        m_path = precision_manager.resolve_onnx_model_file("yolo26n")
        if m_path and m_path.exists():
            return True, f"原生无 NMS 引擎就绪 ({m_path.name})"
        return False, "未找到 yolo26n.int8.onnx，请执行 `glihub_cli.py quantize`"

    def runtime_metadata(self) -> Dict[str, Any]:
        m_path = precision_manager.resolve_onnx_model_file("yolo26n")
        return {
            "active_onnx_file": m_path.name if m_path else None,
            "end2end_no_nms": True,
            "supported_tasks": ["detect", "pose", "seg", "obb"],
        }

    def predict(
        self,
        image_path: Path,
        model_code: str = "yolo26n_rt",
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
    ) -> VisionInferenceOutput:
        self._ensure_loaded()
        if self._runner is None:
            raise RuntimeError("yolo26n ONNX model not initialized")

        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"Cannot decode image: {image_path}")
        h, w = bgr.shape[:2]

        raw, ms = self._runner.infer_bgr(bgr, conf_thres=conf_thres, iou_thres=iou_thres)
        helmets: List[Dict[str, Any]] = []
        h_ms = 0
        if self._helmet_aux is not None and any(r["label"] == "person" for r in raw):
            helmets, h_ms = self._helmet_aux.infer_bgr(bgr, conf_thres=0.30, iou_thres=0.45)

        boxes: List[DetectionBox] = []
        for r in raw:
            lbl = r["label"]
            if lbl == "person" and helmets:
                px1, py1, px2, py2 = r["bbox_xyxy"]
                pw, ph = max(1.0, px2 - px1), max(1.0, py2 - py1)
                hx1, hy1, hx2, hy2 = px1 - 0.12 * pw, max(0.0, py1 - 0.15 * ph), px2 + 0.12 * pw, py1 + 0.45 * ph
                has_h = any(
                    hx1 <= 0.5 * (hm["bbox_xyxy"][0] + hm["bbox_xyxy"][2]) <= hx2
                    and hy1 <= 0.5 * (hm["bbox_xyxy"][1] + hm["bbox_xyxy"][3]) <= hy2
                    for hm in helmets
                )
                if has_h:
                    boxes.append(
                        DetectionBox(
                            label="With Helmet",
                            label_zh="已佩戴安全帽",
                            confidence=r["confidence"],
                            bbox_xyxy=r["bbox_xyxy"],
                            is_violation=False,
                        )
                    )
                else:
                    boxes.append(
                        DetectionBox(
                            label="without_helmet",
                            label_zh="未佩戴安全帽(违章)",
                            confidence=r["confidence"],
                            bbox_xyxy=r["bbox_xyxy"],
                            is_violation=True,
                            violation_reason="YOLO26 实时检测：作业人员未佩戴安全帽",
                        )
                    )
                continue

            is_v = lbl in ("cell phone", "fire", "smoke")
            boxes.append(
                DetectionBox(
                    label=lbl,
                    label_zh=translate_label(lbl),
                    confidence=r["confidence"],
                    bbox_xyxy=r["bbox_xyxy"],
                    is_violation=is_v,
                    violation_reason="现场违章物品/险情特征" if is_v else None,
                )
            )

        save_p, url = render_detections(bgr, boxes, Path(settings.output_dir), prefix="yolo26_int8")
        return VisionInferenceOutput(
            model_code=model_code,
            adapter_type="mod-yolo26-no-nms-int8",
            device=self._runner.active_provider,
            inference_ms=ms + h_ms,
            image_width=w,
            image_height=h,
            annotated_image_path=str(save_p),
            annotated_image_url=url,
            detections=boxes,
            has_violation=any(b.is_violation for b in boxes),
            precision="int8" if ".int8." in self._runner.model_path.name else "fp16",
            plugin_id=self.plugin_id,
        )
