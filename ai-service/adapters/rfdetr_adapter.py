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


class RfDetrAdapter(AbstractVisionDetector):
    """
    适配 RF-DETR（Apache 2.0 实时 DINOv2 Transformer 高精度工业检测器）。
    面向独立 GPU 服务器小样本化工装置场景；无卡/开发机环境自动通过开关控制并支持平滑回退。
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
        self.detector = None

    @property
    def adapter_type(self) -> str:
        return "rfdetr"

    def is_available(self) -> Tuple[bool, str]:
        if not settings.enable_rfdetr:
            return False, "当前为无独立显卡/轻量化模式（ENABLE_RFDETR=false），按需在 GPU 环境开启"
        try:
            import rfdetr  # noqa: F401
        except ImportError:
            return False, "未安装 rfdetr 依赖包"
        return True, "RF-DETR Transformer 检测引擎就绪"

    def load(self) -> None:
        if self.loaded and self.detector is not None:
            return
        from rfdetr import RFDETRBase

        kwargs = {}
        if self.weights_path and self.weights_path.exists():
            kwargs["pretrain_weights"] = str(self.weights_path)
        self.detector = RFDETRBase(**kwargs)
        self.loaded = True

    def predict(
        self,
        image_path: Path,
        conf_thres: float = 0.40,
        iou_thres: float = 0.50,
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
                res.note = f"[GPU按需降级] {reason} -> 已由本地基准检测器兜底执行"
                return res
            raise RuntimeError(reason)

        self.load()
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"无法读取图像: {image_path}")
        h, w = bgr.shape[:2]
        t0 = time.perf_counter()
        sv_dets = self.detector.predict(str(image_path), threshold=conf_thres)
        detections: List[DetectionBox] = []
        for xyxy, conf, cls_id in zip(sv_dets.xyxy, sv_dets.confidence, sv_dets.class_id):
            label = f"rfdetr_cls_{int(cls_id)}"
            detections.append(
                DetectionBox(
                    label=label,
                    label_zh=translate_label(label),
                    confidence=round(float(conf), 4),
                    bbox_xyxy=[float(v) for v in xyxy.tolist()],
                    is_violation=True,
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
