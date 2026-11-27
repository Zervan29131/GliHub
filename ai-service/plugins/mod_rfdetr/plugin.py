from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, List

from PIL import Image

from adapters.base import DetectionBox, VisionInferenceOutput, render_detections, translate_label
from config import settings
from core.plugin_registry import BaseAiPlugin


class RfDetrPlugin(BaseAiPlugin):
    """
    Plugin 3 (`mod-rfdetr`):
    Apache 2.0 RF-DETR Transformer high-precision detector (unlocked in `gpu-pro` profile).
    """

    def __init__(self, manifest: Dict[str, Any]) -> None:
        super().__init__(manifest)
        self._model: Any = None

    def _ensure_loaded(self) -> None:
        if self._model is None:
            from rfdetr import RFDETRBase  # type: ignore

            self._model = RFDETRBase()

    def check_readiness(self) -> tuple[bool, str]:
        return True, "RF-DETR FP16 Transformer 就绪"

    def predict(
        self, image_path: Path, model_code: str = "rfdetr_precision", conf_thres: float = 0.35
    ) -> VisionInferenceOutput:
        self._ensure_loaded()
        pil_img = Image.open(image_path).convert("RGB")
        w, h = pil_img.size
        t0 = time.perf_counter()
        dets = self._model.predict(pil_img, threshold=conf_thres)
        ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))

        boxes: List[DetectionBox] = []
        for xyxy, conf, cid in zip(dets.xyxy, dets.confidence, dets.class_id):
            lbl = f"class_{int(cid)}"
            boxes.append(
                DetectionBox(
                    label=lbl,
                    label_zh=translate_label(lbl),
                    confidence=round(float(conf), 4),
                    bbox_xyxy=[round(float(v), 1) for v in xyxy],
                )
            )
        save_p, url = render_detections(pil_img, boxes, Path(settings.output_dir), prefix="rfdetr_fp16")
        return VisionInferenceOutput(
            model_code=model_code,
            adapter_type="mod-rfdetr-fp16",
            device="cuda",
            inference_ms=ms,
            image_width=w,
            image_height=h,
            annotated_image_path=str(save_p),
            annotated_image_url=url,
            detections=boxes,
            has_violation=any(b.is_violation for b in boxes),
            precision="fp16",
            plugin_id=self.plugin_id,
        )
