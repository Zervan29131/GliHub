import time
from pathlib import Path
from typing import List, Optional, Tuple
import cv2

from adapters.base import (
    AbstractVisionDetector,
    DetectionBox,
    VisionInferenceOutput,
    render_detections,
    translate_label,
)
from config import settings


class Yolo26Adapter(AbstractVisionDetector):
    """
    适配 Ultralytics YOLO26（端到端无 NMS 实时边缘推理引擎）。
    若当前环境未安装 ultralytics 或未缓存 yolo26n.pt 权重，支持优雅降级至存量 yolov5_local 推理。
    """

    def __init__(
        self,
        model_code: str,
        weights_path: Optional[Path],
        device: str = "cpu",
        fallback_detector: Optional[AbstractVisionDetector] = None,
    ):
        super().__init__(model_code=model_code, weights_path=weights_path, device=device)
        self.fallback_detector = fallback_detector
        self.yolo_model = None

    @property
    def adapter_type(self) -> str:
        return "yolo26"

    def is_available(self) -> Tuple[bool, str]:
        if not settings.enable_yolo26:
            return False, "已通过 ENABLE_YOLO26=false 关闭"
        try:
            import ultralytics  # noqa: F401
        except ImportError:
            return False, "未安装 ultralytics 包（当前使用本地 YOLOv5 边缘兼容层无缝代管）"
        if not self.weights_path or not self.weights_path.exists():
            return False, f"本地未缓存 {self.weights_path.name if self.weights_path else 'yolo26n.pt'} 权重（自动回退本地 YOLOv5）"
        return True, "YOLO26 原生无 NMS 引擎就绪"

    def load(self) -> None:
        if self.loaded and self.yolo_model is not None:
            return
        from ultralytics import YOLO

        self.yolo_model = YOLO(str(self.weights_path))
        self.loaded = True

    def predict(
        self,
        image_path: Path,
        conf_thres: float = 0.30,
        iou_thres: float = 0.45,
        prompt_text: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> VisionInferenceOutput:
        ok, reason = self.is_available()
        if not ok:
            if self.fallback_detector is not None:
                res = self.fallback_detector.predict(
                    image_path=image_path,
                    conf_thres=conf_thres,
                    iou_thres=iou_thres,
                    prompt_text=prompt_text,
                    output_dir=output_dir,
                )
                res.model_code = self.model_code
                res.adapter_type = self.adapter_type
                res.fallback_used = True
                res.note = f"[平滑降级] {reason} -> 已自动回退至 yolov5target-main 存量引擎完成检测"
                return res
            raise RuntimeError(reason)

        self.load()
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"无法读取图像: {image_path}")
        h, w = bgr.shape[:2]
        t0 = time.perf_counter()
        results = self.yolo_model.predict(
            source=str(image_path),
            conf=conf_thres,
            iou=iou_thres,
            device=self.device,
            verbose=False,
        )
        detections: List[DetectionBox] = []
        for r in results:
            names = r.names
            for box in r.boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = [float(v) for v in box.xyxy[0].tolist()]
                label = names.get(cls_id, str(cls_id))
                is_viol = label in ("no_helmet", "without_helmet", "smoke", "fire", "cell phone")
                detections.append(
                    DetectionBox(
                        label=label,
                        label_zh=translate_label(label),
                        confidence=round(conf, 4),
                        bbox_xyxy=xyxy,
                        is_violation=is_viol,
                    )
                )

        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
        out_dir = output_dir or Path(settings.output_dir)
        saved_path, saved_url = render_detections(bgr, detections, out_dir, prefix=self.model_code)
        return VisionInferenceOutput(
            model_code=self.model_code,
            adapter_type=self.adapter_type,
            device=self.device,
            inference_ms=elapsed_ms,
            image_width=w,
            image_height=h,
            annotated_image_path=str(saved_path),
            annotated_image_url=saved_url,
            detections=detections,
            has_violation=any(d.is_violation for d in detections),
        )
