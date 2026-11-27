from pathlib import Path
from typing import Dict, List, Optional
import torch

from adapters.base import AbstractVisionDetector, VisionInferenceOutput
from adapters.rfdetr_adapter import RfDetrAdapter
from adapters.yolo26_adapter import Yolo26Adapter
from adapters.yoloe_adapter import YoloEAdapter
from adapters.yolov5_local import YoloV5LocalDetector
from config import settings


def detect_optimal_device(preferred: str = "auto") -> str:
    if preferred and preferred != "auto":
        return preferred
    if torch.cuda.is_available():
        return "cuda"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


class ModelRegistry:
    """
    视觉模型统一策略注册表：
    默认预置并纳管 yolov5target-main 下的两套权重，以及 YOLO26 / RF-DETR / YOLOE 插件化适配器。
    """

    def __init__(self) -> None:
        self.device = detect_optimal_device(settings.default_device)
        self._detectors: Dict[str, AbstractVisionDetector] = {}
        self._init_builtin_models()

    def _init_builtin_models(self) -> None:
        repo = Path(settings.yolov5_repo_dir).resolve()
        helmet_pt = repo / "runs" / "train" / "exp15" / "weights" / "best.pt"
        coco_pt = repo / "yolov5s.pt"

        # YOLOv5 v5.0 旧版切片算子在 CPU/CUDA 最稳定，其他新框架可直接跑 MPS/CUDA
        v5_device = "cuda" if self.device == "cuda" else "cpu"

        helmet_det = YoloV5LocalDetector(
            model_code="yolov5_helmet_local",
            weights_path=helmet_pt,
            device=v5_device,
            coupled_person_weights=coco_pt,
        )
        coco_det = YoloV5LocalDetector(
            model_code="yolov5s_coco_local",
            weights_path=coco_pt,
            device=v5_device,
            coupled_person_weights=None,
        )

        self._detectors["yolov5_helmet_local"] = helmet_det
        self._detectors["yolov5s_coco_local"] = coco_det

        self._detectors["yolo26n_industrial"] = Yolo26Adapter(
            model_code="yolo26n_industrial",
            weights_path=settings.resolve_path("yolo26n.pt"),
            device=self.device,
            fallback_detector=helmet_det,
        )
        self._detectors["rfdetr_chem_hd"] = RfDetrAdapter(
            model_code="rfdetr_chem_hd",
            weights_path=settings.resolve_path("rf-detr-base.pth"),
            device=self.device,
            fallback_detector=coco_det,
        )
        self._detectors["yoloe_zero_shot"] = YoloEAdapter(
            model_code="yoloe_zero_shot",
            weights_path=settings.resolve_path("yoloe-v8s-seg.pt"),
            device=self.device,
            helmet_detector=helmet_det,
            coco_detector=coco_det,
        )

    def register_custom_yolov5(self, model_code: str, weights_path: str) -> None:
        resolved = settings.resolve_path(weights_path)
        v5_device = "cuda" if self.device == "cuda" else "cpu"
        self._detectors[model_code] = YoloV5LocalDetector(
            model_code=model_code,
            weights_path=resolved,
            device=v5_device,
        )

    def list_models(self) -> List[Dict]:
        items = []
        for code, det in self._detectors.items():
            ok, msg = det.is_available()
            items.append(
                {
                    "model_code": code,
                    "adapter_type": det.adapter_type,
                    "device": det.device,
                    "native_ready": ok,
                    "weights_path": str(det.weights_path) if det.weights_path else None,
                    "weights_exists": bool(det.weights_path and det.weights_path.exists()),
                    "loaded": det.loaded,
                    "status_message": msg,
                }
            )
        return items

    def get_detector(self, model_code: Optional[str]) -> AbstractVisionDetector:
        code = model_code or "yolov5_helmet_local"
        if code in self._detectors:
            return self._detectors[code]
        return self._detectors["yolov5_helmet_local"]

    def predict(
        self,
        image_path: Path,
        model_code: Optional[str] = None,
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
        prompt_text: Optional[str] = None,
    ) -> VisionInferenceOutput:
        detector = self.get_detector(model_code)
        return detector.predict(
            image_path=image_path,
            conf_thres=conf_thres,
            iou_thres=iou_thres,
            prompt_text=prompt_text,
        )


registry = ModelRegistry()
