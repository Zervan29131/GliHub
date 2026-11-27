from __future__ import annotations

import ast
import gc
import hashlib
import json
import math
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

import cv2
import numpy as np
import onnxruntime as ort

COCO_NAMES_80: Dict[int, str] = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    24: "backpack", 25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase",
    39: "bottle", 41: "cup", 56: "chair", 62: "tv", 63: "laptop", 67: "cell phone",
}


def compute_sha256(file_path: Path) -> str:
    if not file_path.exists():
        return ""
    h = hashlib.sha256()
    with file_path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def detect_chip_model() -> str:
    sys_name = platform.system()
    machine = platform.machine()
    try:
        if sys_name == "Darwin":
            out = subprocess.check_output(
                ["sysctl", "-n", "machdep.cpu.brand_string"], text=True, timeout=2
            ).strip()
            if out:
                return f"{out} ({machine})"
        elif sys_name == "Linux":
            cpuinfo = Path("/proc/cpuinfo")
            if cpuinfo.exists():
                for line in cpuinfo.read_text(encoding="utf-8", errors="ignore").splitlines():
                    if "model name" in line or "Hardware" in line or "Model" in line:
                        return f"{line.split(':', 1)[-1].strip()} ({machine})"
    except Exception:
        pass
    return f"{platform.processor() or sys_name} ({machine})"


def select_execution_providers(precision_mode: str, model_path: Path) -> Tuple[List[str], str]:
    """
    Hardware auto-detection priority:
    1. CUDA / TensorRT (NVIDIA GPU)
    2. DirectML (Windows GPU/iGPU)
    3. OpenVINO (x86 INT8/FP16)
    4. CoreML (Apple Silicon FP16) / ARM64 CPU KleidiAI INT8 (for QDQ .int8.onnx)
    5. CPUExecutionProvider (AVX2 / VNNI / ARM64 NEON / XNNPACK)
    """
    available = ort.get_available_providers()
    is_int8_model = ".int8." in model_path.name.lower() or precision_mode.lower() == "int8"

    chosen: List[str] = []
    if "TensorrtExecutionProvider" in available:
        chosen.append("TensorrtExecutionProvider")
    if "CUDAExecutionProvider" in available:
        chosen.append("CUDAExecutionProvider")
    if "OpenVINOExecutionProvider" in available:
        chosen.append("OpenVINOExecutionProvider")
    if "DmlExecutionProvider" in available and not is_int8_model:
        chosen.append("DmlExecutionProvider")
    # On Apple Silicon, QDQ Static INT8 runs natively on ARM64 NEON/KleidiAI via CPUExecutionProvider
    # without CoreML subgraph partition fallback overhead; FP16/FP32 uses CoreML.
    if "CoreMLExecutionProvider" in available and not is_int8_model:
        chosen.append("CoreMLExecutionProvider")
    chosen.append("CPUExecutionProvider")

    active_label = chosen[0]
    return chosen, active_label


def letterbox(
    img_bgr: np.ndarray, new_shape: int = 640, color: Tuple[int, int, int] = (114, 114, 114)
) -> Tuple[np.ndarray, float, Tuple[float, float]]:
    h0, w0 = img_bgr.shape[:2]
    r = min(new_shape / max(h0, 1), new_shape / max(w0, 1))
    new_unpad = (int(round(w0 * r)), int(round(h0 * r)))
    dw = (new_shape - new_unpad[0]) / 2.0
    dh = (new_shape - new_unpad[1]) / 2.0

    if (w0, h0) != new_unpad:
        resized = cv2.resize(img_bgr, new_unpad, interpolation=cv2.INTER_LINEAR)
    else:
        resized = img_bgr

    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color)
    return padded, r, (dw, dh)


def xywh2xyxy(x: np.ndarray) -> np.ndarray:
    y = np.empty_like(x)
    half_w = x[..., 2] / 2.0
    half_h = x[..., 3] / 2.0
    y[..., 0] = x[..., 0] - half_w
    y[..., 1] = x[..., 1] - half_h
    y[..., 2] = x[..., 0] + half_w
    y[..., 3] = x[..., 1] + half_h
    return y


def numpy_nms(boxes: np.ndarray, scores: np.ndarray, iou_thres: float = 0.45) -> List[int]:
    if len(boxes) == 0:
        return []
    x1 = boxes[:, 0]
    y1 = boxes[:, 1]
    x2 = boxes[:, 2]
    y2 = boxes[:, 3]
    areas = np.maximum(0.0, x2 - x1) * np.maximum(0.0, y2 - y1)
    order = scores.argsort()[::-1]
    keep: List[int] = []
    while order.size > 0:
        i = int(order[0])
        keep.append(i)
        if order.size == 1:
            break
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        w = np.maximum(0.0, xx2 - xx1)
        h = np.maximum(0.0, yy2 - yy1)
        inter = w * h
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        inds = np.where(iou <= iou_thres)[0]
        order = order[inds + 1]
    return keep


def obb_to_corners(cx: float, cy: float, w: float, h: float, angle_rad: float) -> List[List[float]]:
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)
    dx, dy = w / 2.0, h / 2.0
    offsets = [(-dx, -dy), (dx, -dy), (dx, dy), (-dx, dy)]
    pts: List[List[float]] = []
    for ox, oy in offsets:
        rx = cx + ox * cos_a - oy * sin_a
        ry = cy + ox * sin_a + oy * cos_a
        pts.append([round(rx, 1), round(ry, 1)])
    return pts


class OnnxYoloEngine:
    """
    Unified Low-Precision ONNX Runtime Engine for GliHub 3.0 Edge & Center.
    Supports:
      - YOLO26 native end-to-end no-NMS tensors (`detect`, `pose`, `seg`, `obb`)
      - Classic YOLOv5 / YOLOv8 / YOLOv11 tensors (including custom `yolov5_helmet.int8.onnx`)
      - Zero-downtime atomic hot-reload for OTA updates
    """

    def __init__(
        self,
        model_path: Path,
        precision_mode: str = "int8",
        imgsz: int = 640,
        cpu_threads: int = 0,
        default_names: Optional[Dict[int, str]] = None,
    ) -> None:
        self._lock = threading.RLock()
        self.precision_mode = precision_mode
        self.imgsz = imgsz
        total_cores = os.cpu_count() or 4
        self.cpu_threads = cpu_threads if cpu_threads > 0 else min(4, max(1, total_cores // 2))
        self.default_names = default_names or COCO_NAMES_80

        self.model_path = Path(model_path)
        self.model_sha256 = ""
        self.session: Optional[ort.InferenceSession] = None
        self.input_name = "images"
        self.input_dtype = "tensor(float)"
        self.active_provider = "CPUExecutionProvider"
        self.class_names: Dict[int, str] = dict(self.default_names)
        self.model_task = "detect"
        self.is_end2end = False

        if self.model_path.exists():
            self.reload_model(self.model_path)

    def reload_model(self, new_path: Path) -> Dict[str, Any]:
        target = Path(new_path).resolve()
        if not target.exists():
            raise FileNotFoundError(f"ONNX model not found: {target}")

        providers, _ = select_execution_providers(self.precision_mode, target)
        sess_opts = ort.SessionOptions()
        sess_opts.intra_op_num_threads = self.cpu_threads
        sess_opts.inter_op_num_threads = 1
        sess_opts.enable_cpu_mem_arena = False
        sess_opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        # Release previous session arena before allocating replacement during OTA hot-reload
        with self._lock:
            if self.session is not None:
                self.session = None
                gc.collect()

        new_sess = ort.InferenceSession(str(target), sess_options=sess_opts, providers=providers)
        inp = new_sess.get_inputs()[0]
        inp_shape = inp.shape
        resolved_imgsz = self.imgsz
        if len(inp_shape) == 4 and isinstance(inp_shape[2], int) and inp_shape[2] > 0:
            resolved_imgsz = int(inp_shape[2])

        meta = new_sess.get_modelmeta().custom_metadata_map or {}
        parsed_names = dict(self.default_names)
        if "names" in meta:
            try:
                raw_names = ast.literal_eval(meta["names"])
                if isinstance(raw_names, dict):
                    parsed_names = {int(k): str(v) for k, v in raw_names.items()}
                elif isinstance(raw_names, list):
                    parsed_names = {i: str(v) for i, v in enumerate(raw_names)}
            except Exception:
                pass

        out0_shape = new_sess.get_outputs()[0].shape
        end2end_flag = str(meta.get("end2end", "")).lower() == "true" or (
            len(out0_shape) == 3 and out0_shape[1] in (100, 300)
        )
        task_meta = str(meta.get("task", "detect")).lower()
        sha = compute_sha256(target)

        with self._lock:
            self.session = new_sess
            self.model_path = target
            self.model_sha256 = sha
            self.input_name = inp.name
            self.input_dtype = inp.type
            self.imgsz = resolved_imgsz
            self.active_provider = new_sess.get_providers()[0]
            self.class_names = parsed_names
            self.model_task = task_meta
            self.is_end2end = end2end_flag

        return self.runtime_info()

    def runtime_info(self) -> Dict[str, Any]:
        return {
            "loaded": self.session is not None,
            "model_file": self.model_path.name,
            "model_path": str(self.model_path),
            "model_sha256": self.model_sha256,
            "precision_mode": "int8"
            if ".int8." in self.model_path.name.lower()
            else ("fp16" if ".fp16." in self.model_path.name.lower() else self.precision_mode),
            "active_provider": self.active_provider,
            "available_providers": ort.get_available_providers(),
            "cpu_threads": self.cpu_threads,
            "imgsz": self.imgsz,
            "is_end2end_no_nms": self.is_end2end,
            "model_task": self.model_task,
            "num_classes": len(self.class_names),
            "os_arch": f"{platform.system().lower()}-{platform.machine().lower()}",
            "chip_model": detect_chip_model(),
        }

    def infer(
        self,
        img_bgr: np.ndarray,
        task_type: str = "detect",
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
    ) -> Tuple[List[Dict[str, Any]], float]:
        with self._lock:
            sess = self.session
            inp_name = self.input_name
            inp_dtype = self.input_dtype
            imgsz = self.imgsz
            names = self.class_names

        if sess is None:
            return [], 0.0

        h0, w0 = img_bgr.shape[:2]
        padded, ratio, (dw, dh) = letterbox(img_bgr, new_shape=imgsz)
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        blob = rgb.transpose(2, 0, 1).astype(np.float32) / 255.0
        blob = np.expand_dims(blob, axis=0)
        if "float16" in inp_dtype:
            blob = blob.astype(np.float16)

        t0 = time.perf_counter()
        outputs = sess.run(None, {inp_name: blob})
        latency_ms = (time.perf_counter() - t0) * 1000.0

        out0 = outputs[0].astype(np.float32)
        proto = outputs[1].astype(np.float32) if len(outputs) > 1 else None
        effective_task = (task_type or self.model_task or "detect").lower()

        dets = self._decode_outputs(
            out0=out0,
            proto=proto,
            task_type=effective_task,
            conf_thres=conf_thres,
            iou_thres=iou_thres,
            ratio=ratio,
            dw=dw,
            dh=dh,
            orig_w=w0,
            orig_h=h0,
            imgsz=imgsz,
            names=names,
        )
        return dets, latency_ms

    def _scale_xyxy(
        self, x1: float, y1: float, x2: float, y2: float, ratio: float, dw: float, dh: float, w0: int, h0: int
    ) -> List[float]:
        sx1 = max(0.0, min(float(w0), (float(x1) - float(dw)) / float(ratio)))
        sy1 = max(0.0, min(float(h0), (float(y1) - float(dh)) / float(ratio)))
        sx2 = max(0.0, min(float(w0), (float(x2) - float(dw)) / float(ratio)))
        sy2 = max(0.0, min(float(h0), (float(y2) - float(dh)) / float(ratio)))
        return [round(float(sx1), 1), round(float(sy1), 1), round(float(sx2), 1), round(float(sy2), 1)]

    def _decode_outputs(
        self,
        out0: np.ndarray,
        proto: Optional[np.ndarray],
        task_type: str,
        conf_thres: float,
        iou_thres: float,
        ratio: float,
        dw: float,
        dh: float,
        orig_w: int,
        orig_h: int,
        imgsz: int,
        names: Dict[int, str],
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        pred = out0[0] if out0.ndim == 3 else out0

        # Branch A: YOLO26 End-to-End No-NMS output -> shape (300, C) where C in {6, 7, 38, 57}
        if pred.shape[0] in (100, 300) and pred.shape[1] >= 6 and pred.shape[1] <= 128:
            for row in pred:
                score = float(row[4])
                if score < conf_thres:
                    continue
                cls_id = int(round(float(row[5])))
                cls_name = names.get(cls_id, f"class_{cls_id}")

                if task_type == "obb" and pred.shape[1] == 7:
                    # [cx, cy, w, h, conf, cls, angle_rad]
                    cx = (float(row[0]) - dw) / ratio
                    cy = (float(row[1]) - dh) / ratio
                    bw = float(row[2]) / ratio
                    bh = float(row[3]) / ratio
                    ang = float(row[6])
                    poly = obb_to_corners(cx, cy, bw, bh, ang)
                    xs = [p[0] for p in poly]
                    ys = [p[1] for p in poly]
                    bbox = [
                        round(max(0.0, min(xs)), 1),
                        round(max(0.0, min(ys)), 1),
                        round(min(float(orig_w), max(xs)), 1),
                        round(min(float(orig_h), max(ys)), 1),
                    ]
                    results.append(
                        {
                            "class_id": cls_id,
                            "class_name": cls_name,
                            "confidence": round(score, 4),
                            "bbox": bbox,
                            "task_type": "obb",
                            "obb_corners": poly,
                            "angle_deg": round(math.degrees(ang), 1),
                        }
                    )
                    continue

                bbox = self._scale_xyxy(row[0], row[1], row[2], row[3], ratio, dw, dh, orig_w, orig_h)
                item: Dict[str, Any] = {
                    "class_id": cls_id,
                    "class_name": cls_name,
                    "confidence": round(score, 4),
                    "bbox": bbox,
                    "task_type": task_type,
                }

                # Pose 17 keypoints
                if (task_type == "pose" or pred.shape[1] >= 56) and pred.shape[1] >= 56:
                    kpts_raw = row[6:57].reshape(-1, 3)
                    kpts: List[List[float]] = []
                    for kx, ky, kc in kpts_raw:
                        skx = round(max(0.0, min(float(orig_w), (float(kx) - dw) / ratio)), 1)
                        sky = round(max(0.0, min(float(orig_h), (float(ky) - dh) / ratio)), 1)
                        kpts.append([skx, sky, round(float(kc), 3)])
                    item["keypoints"] = kpts
                    item["task_type"] = "pose"
                    bw = max(1.0, bbox[2] - bbox[0])
                    bh = max(1.0, bbox[3] - bbox[1])
                    if bw / bh > 1.32:
                        item["posture_alert"] = "FALL_SUSPECTED"
                        item["label_cn"] = "疑似人员跌倒/晕倒姿态"
                        item["is_violation"] = True

                # Instance segmentation mask coefficients
                elif (task_type in ("seg", "segment") or pred.shape[1] == 38) and proto is not None and pred.shape[1] >= 38:
                    coeffs = row[6:38]
                    p_mat = proto[0]  # (32, mh, mw)
                    mh, mw = p_mat.shape[1], p_mat.shape[2]
                    mask_logits = np.tensordot(coeffs, p_mat, axes=([0], [0]))
                    mask_prob = 1.0 / (1.0 + np.exp(-np.clip(mask_logits, -20.0, 20.0)))
                    scale_m = mh / float(imgsz)
                    mx1 = max(0, int(row[0] * scale_m))
                    my1 = max(0, int(row[1] * scale_m))
                    mx2 = min(mw, int(math.ceil(row[2] * scale_m)))
                    my2 = min(mh, int(math.ceil(row[3] * scale_m)))
                    cropped = np.zeros_like(mask_prob, dtype=np.uint8)
                    if mx2 > mx1 and my2 > my1:
                        cropped[my1:my2, mx1:mx2] = (mask_prob[my1:my2, mx1:mx2] > 0.5).astype(np.uint8)
                    mask_ratio = float(cropped.sum()) / float(max(1, mh * mw))
                    item["mask_area_ratio"] = round(mask_ratio, 5)
                    item["task_type"] = "seg"

                results.append(item)
            return results

        # Branch B: YOLOv5 classic output -> shape (25200, 5 + nc) with objectness at idx 4
        if pred.shape[0] >= 1000 and pred.shape[1] == len(names) + 5:
            obj_mask = pred[:, 4] >= conf_thres
            cand = pred[obj_mask]
            if len(cand) == 0:
                return []
            cls_probs = cand[:, 5:] * cand[:, 4:5]
            cls_ids = np.argmax(cls_probs, axis=1)
            scores = cls_probs[np.arange(len(cand)), cls_ids]
            keep_mask = scores >= conf_thres
            cand = cand[keep_mask]
            scores = scores[keep_mask]
            cls_ids = cls_ids[keep_mask]
            if len(cand) == 0:
                return []
            boxes_xyxy = xywh2xyxy(cand[:, :4])
            keep_idx = numpy_nms(boxes_xyxy, scores, iou_thres=iou_thres)
            for idx in keep_idx[:100]:
                cid = int(cls_ids[idx])
                b = boxes_xyxy[idx]
                results.append(
                    {
                        "class_id": cid,
                        "class_name": names.get(cid, f"class_{cid}"),
                        "confidence": round(float(scores[idx]), 4),
                        "bbox": self._scale_xyxy(b[0], b[1], b[2], b[3], ratio, dw, dh, orig_w, orig_h),
                        "task_type": "detect",
                    }
                )
            return results

        # Branch C: YOLOv8 / YOLOv11 transposed output -> shape (4 + nc + extra, 8400)
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T
        nc = max(1, len(names))
        if pred.shape[1] >= 4 + nc:
            cls_scores = pred[:, 4 : 4 + nc]
            cls_ids = np.argmax(cls_scores, axis=1)
            scores = cls_scores[np.arange(len(pred)), cls_ids]
            mask = scores >= conf_thres
            cand = pred[mask]
            scores = scores[mask]
            cls_ids = cls_ids[mask]
            if len(cand) == 0:
                return []
            boxes_xyxy = xywh2xyxy(cand[:, :4])
            keep_idx = numpy_nms(boxes_xyxy, scores, iou_thres=iou_thres)
            for idx in keep_idx[:100]:
                cid = int(cls_ids[idx])
                b = boxes_xyxy[idx]
                results.append(
                    {
                        "class_id": cid,
                        "class_name": names.get(cid, f"class_{cid}"),
                        "confidence": round(float(scores[idx]), 4),
                        "bbox": self._scale_xyxy(b[0], b[1], b[2], b[3], ratio, dw, dh, orig_w, orig_h),
                        "task_type": task_type,
                    }
                )
        return results
