from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2

from adapters.base import DetectionBox, VisionInferenceOutput, render_detections, translate_label
from config import settings
from core.plugin_registry import BaseAiPlugin
from core.precision import LowPrecisionOnnxRunner, precision_manager


class YoloV5Plugin(BaseAiPlugin):
    """
    Plugin 1 (`mod-yolov5`):
    Runs quantized `yolov5_helmet.int8.onnx` (exported from `yolov5target-main/runs/train/exp15/weights/best.pt`)
    coupled with lightweight person detection (`yolo26n.int8.onnx`) to identify both `With Helmet` and `without_helmet`.
    Zero PyTorch dependency at runtime!
    """

    def __init__(self, manifest: Dict[str, Any]) -> None:
        super().__init__(manifest)
        self._helmet_runner: Optional[LowPrecisionOnnxRunner] = None
        self._person_runner: Optional[LowPrecisionOnnxRunner] = None
        self._custom_runners: Dict[str, LowPrecisionOnnxRunner] = {}

    def _ensure_loaded(self) -> None:
        if self._helmet_runner is None:
            h_path = precision_manager.resolve_onnx_model_file("yolov5_helmet")
            if h_path and h_path.exists():
                self._helmet_runner = LowPrecisionOnnxRunner(h_path, default_names={0: "With Helmet"})
        if self._person_runner is None and settings.yolov5_coupled_person_check:
            p_path = precision_manager.resolve_onnx_model_file("yolo26n")
            if p_path and p_path.exists():
                self._person_runner = LowPrecisionOnnxRunner(p_path)

    def check_readiness(self) -> tuple[bool, str]:
        h_path = precision_manager.resolve_onnx_model_file("yolov5_helmet")
        if h_path and h_path.exists():
            return True, f"已挂载量化权重 {h_path.name}"
        best_pt = Path(settings.yolov5_repo_dir) / "runs" / "train" / "exp15" / "weights" / "best.pt"
        if best_pt.exists():
            return False, "检测到原 best.pt，请运行 `glihub_cli.py quantize` 导出 ONNX INT8"
        return False, "未找到 yolov5_helmet.int8.onnx 权重"

    def runtime_metadata(self) -> Dict[str, Any]:
        h_path = precision_manager.resolve_onnx_model_file("yolov5_helmet")
        return {
            "yolov5_repo_discovered": str(settings.yolov5_repo_dir),
            "yolov5_repo_exists": Path(settings.yolov5_repo_dir).exists(),
            "active_onnx_file": h_path.name if h_path else None,
            "coupled_person_check": settings.yolov5_coupled_person_check,
        }

    def register_custom_weight(self, model_code: str, weights_path: str) -> None:
        resolved = settings.resolve_path(weights_path)
        if not resolved or not resolved.exists():
            raise FileNotFoundError(f"Weight not found: {weights_path}")
        if resolved.suffix.lower() == ".onnx":
            self._custom_runners[model_code] = LowPrecisionOnnxRunner(resolved)
        else:
            # Map legacy .pt registration to matching quantized .int8.onnx if exported
            h_path = precision_manager.resolve_onnx_model_file("yolov5_helmet")
            if h_path:
                self._custom_runners[model_code] = LowPrecisionOnnxRunner(h_path, default_names={0: "With Helmet"})

    def predict(
        self,
        image_path: Path,
        model_code: str = "yolov5_helmet_local",
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
    ) -> VisionInferenceOutput:
        self._ensure_loaded()
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"Cannot decode image: {image_path}")
        h, w = bgr.shape[:2]

        if model_code in self._custom_runners:
            runner = self._custom_runners[model_code]
            raw, ms = runner.infer_bgr(bgr, conf_thres=conf_thres, iou_thres=iou_thres)
            boxes = [
                DetectionBox(
                    label=r["label"],
                    label_zh=translate_label(r["label"]),
                    confidence=r["confidence"],
                    bbox_xyxy=r["bbox_xyxy"],
                    is_violation=r["label"] in ("without_helmet", "no_helmet", "cell phone"),
                )
                for r in raw
            ]
            save_p, url = render_detections(bgr, boxes, Path(settings.output_dir), prefix=model_code)
            return VisionInferenceOutput(
                model_code=model_code,
                adapter_type="mod-yolov5-onnx",
                device=runner.active_provider,
                inference_ms=ms,
                image_width=w,
                image_height=h,
                annotated_image_path=str(save_p),
                annotated_image_url=url,
                detections=boxes,
                has_violation=any(b.is_violation for b in boxes),
                precision="int8" if ".int8." in runner.model_path.name else "fp16",
                plugin_id=self.plugin_id,
            )

        if model_code == "yolov5s_coco_local" and self._person_runner is not None:
            raw, ms = self._person_runner.infer_bgr(bgr, conf_thres=conf_thres, iou_thres=iou_thres)
            boxes = [
                DetectionBox(
                    label=r["label"],
                    label_zh=translate_label(r["label"]),
                    confidence=r["confidence"],
                    bbox_xyxy=r["bbox_xyxy"],
                    is_violation=(r["label"] == "cell phone"),
                    violation_reason="防爆区违规使用手机" if r["label"] == "cell phone" else None,
                )
                for r in raw
            ]
            save_p, url = render_detections(bgr, boxes, Path(settings.output_dir), prefix=model_code)
            return VisionInferenceOutput(
                model_code=model_code,
                adapter_type="mod-yolov5-onnx",
                device=self._person_runner.active_provider,
                inference_ms=ms,
                image_width=w,
                image_height=h,
                annotated_image_path=str(save_p),
                annotated_image_url=url,
                detections=boxes,
                has_violation=any(b.is_violation for b in boxes),
                precision="int8",
                plugin_id=self.plugin_id,
            )

        if self._helmet_runner is None:
            raise RuntimeError("yolov5_helmet ONNX model is not available")

        helmets, h_ms = self._helmet_runner.infer_bgr(bgr, conf_thres=max(0.28, conf_thres), iou_thres=iou_thres)
        persons: List[Dict[str, Any]] = []
        p_ms = 0
        if self._person_runner is not None:
            p_raw, p_ms = self._person_runner.infer_bgr(bgr, conf_thres=conf_thres, iou_thres=iou_thres)
            persons = [p for p in p_raw if p["label"] in ("person", "cell phone")]

        boxes: List[DetectionBox] = []
        used_h = set()
        for p in persons:
            if p["label"] == "cell phone":
                boxes.append(
                    DetectionBox(
                        label="cell phone",
                        label_zh=translate_label("cell phone"),
                        confidence=p["confidence"],
                        bbox_xyxy=p["bbox_xyxy"],
                        is_violation=True,
                        violation_reason="高危场所违规使用通讯设备",
                    )
                )
                continue

            px1, py1, px2, py2 = p["bbox_xyxy"]
            pw, ph = max(1.0, px2 - px1), max(1.0, py2 - py1)
            hx1, hy1, hx2, hy2 = px1 - 0.12 * pw, max(0.0, py1 - 0.15 * ph), px2 + 0.12 * pw, py1 + 0.45 * ph

            matched_idx = None
            for idx, hm in enumerate(helmets):
                bx1, by1, bx2, by2 = hm["bbox_xyxy"]
                cx, cy = 0.5 * (bx1 + bx2), 0.5 * (by1 + by2)
                inter = max(0.0, min(hx2, bx2) - max(hx1, bx1)) * max(0.0, min(hy2, by2) - max(hy1, by1))
                h_area = max(1.0, (bx2 - bx1) * (by2 - by1))
                if (hx1 <= cx <= hx2 and hy1 <= cy <= hy2) or (inter / h_area >= 0.25):
                    matched_idx = idx
                    used_h.add(idx)
                    break

            if matched_idx is not None:
                hm = helmets[matched_idx]
                boxes.append(
                    DetectionBox(
                        label="With Helmet",
                        label_zh="已佩戴安全帽",
                        confidence=hm["confidence"],
                        bbox_xyxy=hm["bbox_xyxy"],
                        is_violation=False,
                    )
                )
            else:
                boxes.append(
                    DetectionBox(
                        label="without_helmet",
                        label_zh="未佩戴安全帽(违章)",
                        confidence=p["confidence"],
                        bbox_xyxy=p["bbox_xyxy"],
                        is_violation=True,
                        violation_reason="作业人员头部区域未检出安全帽",
                    )
                )

        for idx, hm in enumerate(helmets):
            if idx not in used_h:
                boxes.append(
                    DetectionBox(
                        label="With Helmet",
                        label_zh="已佩戴安全帽",
                        confidence=hm["confidence"],
                        bbox_xyxy=hm["bbox_xyxy"],
                        is_violation=False,
                    )
                )

        save_p, url = render_detections(bgr, boxes, Path(settings.output_dir), prefix="yolov5_int8")
        return VisionInferenceOutput(
            model_code=model_code,
            adapter_type="mod-yolov5-int8-onnx",
            device=self._helmet_runner.active_provider,
            inference_ms=h_ms + p_ms,
            image_width=w,
            image_height=h,
            annotated_image_path=str(save_p),
            annotated_image_url=url,
            detections=boxes,
            has_violation=any(b.is_violation for b in boxes),
            precision="int8" if ".int8." in self._helmet_runner.model_path.name else "fp16",
            plugin_id=self.plugin_id,
        )
