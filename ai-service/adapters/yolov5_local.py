from contextlib import contextmanager
import inspect
import os
import pathlib
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple

import cv2
import numpy as np
import torch
import torch.nn as nn

from adapters.base import (
    AbstractVisionDetector,
    DetectionBox,
    VisionInferenceOutput,
    render_detections,
    translate_label,
)
from config import settings


@contextmanager
def _yolov5_legacy_unpickle_ctx(yolov5_repo: Path):
    """
    无侵入兼容补丁上下文：
    1. 修复 Windows 训练权重 (exp15/weights/best.pt) 在 macOS/Linux 反序列化 WindowsPath 报错；
    2. 临时挂载 yolov5target-main 路径，支持反序列化 models.yolo.Model 与 utils.*。
    """
    orig_win_path = getattr(pathlib, "WindowsPath", None)
    repo_str = str(yolov5_repo.resolve())
    inserted = False
    if os.name != "nt":
        pathlib.WindowsPath = pathlib.PosixPath  # type: ignore[assignment]
    if repo_str not in sys.path:
        sys.path.insert(0, repo_str)
        inserted = True
    try:
        yield
    finally:
        if os.name != "nt" and orig_win_path is not None:
            pathlib.WindowsPath = orig_win_path  # type: ignore[assignment]
        if inserted and repo_str in sys.path:
            sys.path.remove(repo_str)


def _torch_load_legacy(weight_file: Path, map_location: torch.device):
    sig = inspect.signature(torch.load)
    if "weights_only" in sig.parameters:
        return torch.load(str(weight_file), map_location=map_location, weights_only=False)
    return torch.load(str(weight_file), map_location=map_location)


def _letterbox(
    im: np.ndarray,
    new_shape: Tuple[int, int] = (640, 640),
    color: Tuple[int, int, int] = (114, 114, 114),
    stride: int = 32,
) -> Tuple[np.ndarray, Tuple[float, float], Tuple[float, float]]:
    shape = im.shape[:2]  # [h, w]
    r = min(new_shape[0] / shape[0], new_shape[1] / shape[1])
    new_unpad = int(round(shape[1] * r)), int(round(shape[0] * r))
    dw, dh = new_shape[1] - new_unpad[0], new_shape[0] - new_unpad[1]
    dw = np.mod(dw, stride) / 2
    dh = np.mod(dh, stride) / 2

    if shape[::-1] != new_unpad:
        im = cv2.resize(im, new_unpad, interpolation=cv2.INTER_LINEAR)
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    im = cv2.copyMakeBorder(im, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return im, (r, r), (dw, dh)


def _box_head_overlap_ratio(person_xyxy: List[float], helmet_xyxy: List[float]) -> float:
    px1, py1, px2, py2 = person_xyxy
    ph = max(1.0, py2 - py1)
    # 取人体框上部 45%（并向上扩充 10% 容差）作为头肩安全帽匹配区域
    hx1, hy1, hx2, hy2 = px1 - 0.08 * (px2 - px1), max(0.0, py1 - 0.12 * ph), px2 + 0.08 * (px2 - px1), py1 + 0.45 * ph
    bx1, by1, bx2, by2 = helmet_xyxy
    inter_w = max(0.0, min(hx2, bx2) - max(hx1, bx1))
    inter_h = max(0.0, min(hy2, by2) - max(hy1, by1))
    inter_area = inter_w * inter_h
    helmet_area = max(1.0, (bx2 - bx1) * (by2 - by1))
    return inter_area / helmet_area


class YoloV5LocalDetector(AbstractVisionDetector):
    """
    封装并桥接 ../yolov5target-main 存量 YOLOv5 v5.0 模型与权重：
    - 支持加载 runs/train/exp15/weights/best.pt (安全帽自训模型) 与 yolov5s.pt (COCO 80类)；
    - 针对安全帽模型 names=['With Helmet']，自动耦合本地 yolov5s.pt 的 person 检测框，
      精准反推出未佩戴安全帽人员 (without_helmet) 违章框！
    """

    def __init__(
        self,
        model_code: str,
        weights_path: Optional[Path],
        device: str = "cpu",
        coupled_person_weights: Optional[Path] = None,
    ):
        super().__init__(model_code=model_code, weights_path=weights_path, device=device)
        self.yolov5_repo = Path(settings.yolov5_repo_dir).resolve()
        self.coupled_person_weights = coupled_person_weights
        self.model = None
        self.person_model = None
        self.names: List[str] = []
        self.stride: int = 32
        self._nms_fn = None
        self._scale_coords_fn = None

    @property
    def adapter_type(self) -> str:
        return "yolov5_local"

    def is_available(self) -> Tuple[bool, str]:
        if not self.yolov5_repo.exists():
            return False, f"未找到存量目录: {self.yolov5_repo}"
        if not self.weights_path or not self.weights_path.exists():
            return False, f"权重文件不存在: {self.weights_path}"
        return True, "就绪（本地 yolov5target-main 权重已挂载）"

    def _load_single_v5_ckpt(self, weight_file: Path, map_dev: torch.device):
        with _yolov5_legacy_unpickle_ctx(self.yolov5_repo):
            from models.common import Conv
            from utils.general import non_max_suppression, scale_coords

            self._nms_fn = non_max_suppression
            self._scale_coords_fn = scale_coords

            ckpt = _torch_load_legacy(weight_file, map_dev)
            net = (ckpt.get("ema") or ckpt["model"]).float().fuse().eval()
            for m in net.modules():
                if type(m) in [nn.Hardswish, nn.LeakyReLU, nn.ReLU, nn.ReLU6, nn.SiLU]:
                    m.inplace = True
                elif type(m) is Conv:
                    m._non_persistent_buffers_set = set()
                elif isinstance(m, nn.Upsample):
                    # 修复 PyTorch 2.x 下旧序列化 nn.Upsample 缺少 recompute_scale_factor 属性报错
                    if not hasattr(m, "recompute_scale_factor"):
                        m.recompute_scale_factor = None
            return net.to(map_dev)

    def load(self) -> None:
        if self.loaded and self.model is not None:
            return
        ok, msg = self.is_available()
        if not ok:
            raise FileNotFoundError(msg)

        # YOLOv5 v5.0 Focus/NMS 算子在 CPU 与 CUDA 上最稳定；MPS 部分切片回退 CPU 时优先保障零误差
        run_dev_str = self.device if self.device in ("cuda", "mps", "cpu") else "cpu"
        map_dev = torch.device(run_dev_str)
        try:
            self.model = self._load_single_v5_ckpt(self.weights_path, map_dev)
        except Exception:
            map_dev = torch.device("cpu")
            self.device = "cpu"
            self.model = self._load_single_v5_ckpt(self.weights_path, map_dev)

        raw_names = self.model.module.names if hasattr(self.model, "module") else self.model.names
        self.names = [raw_names[i] for i in range(len(raw_names))] if isinstance(raw_names, dict) else list(raw_names)
        self.stride = int(self.model.stride.max()) if hasattr(self.model, "stride") else 32

        # 若当前是单类安全帽模型 ['With Helmet'] 且开启人员耦合，则挂载本地 yolov5s.pt 辅助检出未戴安全帽人员
        if (
            settings.yolov5_coupled_person_check
            and self.names == ["With Helmet"]
            and self.coupled_person_weights
            and self.coupled_person_weights.exists()
        ):
            self.person_model = self._load_single_v5_ckpt(self.coupled_person_weights, map_dev)

        self.loaded = True

    def _infer_net(
        self,
        net,
        bgr_img: np.ndarray,
        conf_thres: float,
        iou_thres: float,
        classes: Optional[List[int]] = None,
    ) -> np.ndarray:
        padded, _, _ = _letterbox(bgr_img, new_shape=(640, 640), stride=self.stride)
        rgb = padded[:, :, ::-1].transpose(2, 0, 1)
        rgb = np.ascontiguousarray(rgb)
        tensor = torch.from_numpy(rgb).to(torch.device(self.device)).float() / 255.0
        if tensor.ndimension() == 3:
            tensor = tensor.unsqueeze(0)

        with torch.no_grad():
            pred = net(tensor, augment=False)[0]
            # NMS 在 CPU 上执行可避免早期 MPS torchvision::nms 兼容差异
            pred_cpu = pred.detach().cpu()
            det_list = self._nms_fn(pred_cpu, conf_thres=conf_thres, iou_thres=iou_thres, classes=classes)

        det = det_list[0]
        if det is None or len(det) == 0:
            return np.zeros((0, 6), dtype=np.float32)

        det[:, :4] = self._scale_coords_fn(tensor.shape[2:], det[:, :4], bgr_img.shape).round()
        return det.numpy()

    def predict(
        self,
        image_path: Path,
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
        prompt_text: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> VisionInferenceOutput:
        self.load()
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"无法解码图像文件: {image_path}")

        h, w = bgr.shape[:2]
        t0 = time.perf_counter()

        raw_dets = self._infer_net(self.model, bgr, conf_thres=conf_thres, iou_thres=iou_thres)
        detections: List[DetectionBox] = []
        helmet_boxes: List[List[float]] = []

        for x1, y1, x2, y2, conf, cls_idx in raw_dets:
            cls_id = int(cls_idx)
            label = self.names[cls_id] if 0 <= cls_id < len(self.names) else f"class_{cls_id}"
            xyxy = [float(x1), float(y1), float(x2), float(y2)]
            is_violation = label in ("cell phone", "without_helmet", "no_helmet", "smoke", "fire")
            reason = "高危作业区违规使用手机" if label == "cell phone" else None
            if label == "With Helmet":
                helmet_boxes.append(xyxy)
            detections.append(
                DetectionBox(
                    label=label,
                    label_zh=translate_label(label),
                    confidence=round(float(conf), 4),
                    bbox_xyxy=xyxy,
                    is_violation=is_violation,
                    violation_reason=reason,
                )
            )

        note = None
        if self.person_model is not None:
            person_dets = self._infer_net(
                self.person_model, bgr, conf_thres=max(0.30, conf_thres), iou_thres=iou_thres, classes=[0]
            )
            unprotected_count = 0
            for px1, py1, px2, py2, pconf, _ in person_dets:
                p_xyxy = [float(px1), float(py1), float(px2), float(py2)]
                matched = any(_box_head_overlap_ratio(p_xyxy, h_xyxy) >= 0.22 for h_xyxy in helmet_boxes)
                if not matched:
                    unprotected_count += 1
                    detections.append(
                        DetectionBox(
                            label="without_helmet",
                            label_zh=translate_label("without_helmet"),
                            confidence=round(float(pconf), 4),
                            bbox_xyxy=p_xyxy,
                            is_violation=True,
                            violation_reason="检测到现场作业人员头肩区域未佩戴安全帽",
                        )
                    )
            note = f"已启用「安全帽自训模型 + 人员耦合反推」双检模式（检出未戴安全帽候选 {unprotected_count} 人）"

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
            fallback_used=False,
            note=note,
        )
