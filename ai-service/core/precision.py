from __future__ import annotations

import ast
import gc
import hashlib
import math
import os
import platform
import subprocess
import threading
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from config import settings

COCO_NAMES_80: Dict[int, str] = {
    0: "person", 1: "bicycle", 2: "car", 3: "motorcycle", 4: "airplane",
    5: "bus", 6: "train", 7: "truck", 8: "boat", 9: "traffic light",
    10: "fire hydrant", 11: "stop sign", 12: "parking meter", 13: "bench",
    24: "backpack", 25: "umbrella", 26: "handbag", 27: "tie", 28: "suitcase",
    39: "bottle", 41: "cup", 56: "chair", 62: "tv", 63: "laptop", 67: "cell phone",
}

PROFILE_PRESETS: Dict[str, Dict[str, Any]] = {
    "cpu-int8": {
        "title": "纯 CPU 极速低精度档 (cpu-int8)",
        "target_hardware": "8GB 无独显办公本 / 2C4G 轻量云主机",
        "vision_precision": "int8",
        "imgsz": 640,
        "allow_gpu_heavy": False,
        "recommended_plugins": ["mod-yolov5", "mod-yolo26", "mod-vlm", "mod-llm-rag", "mod-ocr"],
        "llm_vlm_mode": "远端 OpenAI 兼容 API 或内置确定性规则/注册安全工程师模板兜底",
    },
    "local-q4": {
        "title": "本地全离线 4-bit 量化档 (local-q4)",
        "target_hardware": "16GB Apple Silicon Mac / 8G~12G 显存工作站",
        "vision_precision": "int8",
        "imgsz": 640,
        "allow_gpu_heavy": False,
        "recommended_plugins": ["mod-yolov5", "mod-yolo26", "mod-yoloe", "mod-vlm", "mod-llm-rag", "mod-ocr"],
        "llm_vlm_mode": "本地 Ollama / llama.cpp 运行 GGUF Q4_K_M (qwen3-vl:4b + qwen3:8b)",
    },
    "gpu-pro": {
        "title": "企业级独显全开档 (gpu-pro)",
        "target_hardware": "24GB+ NVIDIA GPU 服务器",
        "vision_precision": "fp16",
        "imgsz": 640,
        "allow_gpu_heavy": True,
        "recommended_plugins": [
            "mod-yolov5", "mod-yolo26", "mod-rfdetr", "mod-yoloe", "mod-vlm", "mod-llm-rag", "mod-ocr"
        ],
        "llm_vlm_mode": "本地 vLLM / TensorRT FP16 全模型并发推理",
    },
}


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
                    if "model name" in line or "Hardware" in line:
                        return f"{line.split(':', 1)[-1].strip()} ({machine})"
    except Exception:
        pass
    return f"{platform.processor() or sys_name} ({machine})"


def sha256_digest(path: Path) -> str:
    if not path.exists():
        return ""
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class PrecisionManager:
    """
    GliHub 3.0 Hardware & Low-Precision Quantization Manager.
    Detects accelerator capabilities without requiring PyTorch to be installed!
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.deploy_profile = settings.deploy_profile if settings.deploy_profile in PROFILE_PRESETS else "cpu-int8"
        self.preferred_precision = settings.default_precision or PROFILE_PRESETS[self.deploy_profile]["vision_precision"]
        self.imgsz = int(settings.default_imgsz or 640)
        total_cores = os.cpu_count() or 4
        self.cpu_threads = settings.cpu_threads if settings.cpu_threads > 0 else min(4, max(1, total_cores // 2))

    def detect_hardware(self) -> Dict[str, Any]:
        ort_available = False
        providers: List[str] = []
        try:
            import onnxruntime as ort  # type: ignore

            ort_available = True
            providers = list(ort.get_available_providers())
        except ImportError:
            providers = []

        has_cuda = "CUDAExecutionProvider" in providers or "TensorrtExecutionProvider" in providers
        has_coreml = "CoreMLExecutionProvider" in providers
        has_dml = "DmlExecutionProvider" in providers
        has_openvino = "OpenVINOExecutionProvider" in providers

        # Also check torch CUDA/MPS if torch happens to be installed in gpu-pro / local-q4
        torch_cuda = False
        torch_mps = False
        try:
            import torch  # type: ignore

            torch_cuda = bool(torch.cuda.is_available())
            torch_mps = bool(hasattr(torch.backends, "mps") and torch.backends.mps.is_available())
        except ImportError:
            pass

        if has_cuda or torch_cuda:
            tier = "cuda"
        elif has_coreml or torch_mps:
            tier = "apple-silicon"
        elif has_dml:
            tier = "directml"
        elif has_openvino:
            tier = "openvino-x86"
        else:
            tier = f"cpu-{platform.machine().lower()}"

        return {
            "os_arch": f"{platform.system().lower()}-{platform.machine().lower()}",
            "chip_model": detect_chip_model(),
            "accelerator_tier": tier,
            "has_dedicated_gpu": bool(has_cuda or torch_cuda),
            "has_apple_neural_or_mps": bool(has_coreml or torch_mps),
            "onnxruntime_installed": ort_available,
            "available_ort_providers": providers,
            "deploy_profile": self.deploy_profile,
            "profile_detail": PROFILE_PRESETS.get(self.deploy_profile, PROFILE_PRESETS["cpu-int8"]),
            "preferred_precision": self.preferred_precision,
            "imgsz": self.imgsz,
            "cpu_threads": self.cpu_threads,
        }

    def update_profile(
        self, deploy_profile: Optional[str] = None, preferred_precision: Optional[str] = None, imgsz: Optional[int] = None
    ) -> Dict[str, Any]:
        with self._lock:
            if deploy_profile and deploy_profile in PROFILE_PRESETS:
                self.deploy_profile = deploy_profile
                if not preferred_precision:
                    self.preferred_precision = PROFILE_PRESETS[deploy_profile]["vision_precision"]
            if preferred_precision in ("int8", "fp16", "fp32", "auto"):
                self.preferred_precision = preferred_precision
            if imgsz in (320, 416, 512, 640, 960, 1280):
                self.imgsz = int(imgsz)
        return self.detect_hardware()

    def resolve_onnx_model_file(self, stem: str) -> Optional[Path]:
        """Selects `.int8.onnx` -> `.fp16.onnx` -> `.onnx` in `./data/models/` based on active precision."""
        models_dir = Path(settings.models_dir)
        prec = self.preferred_precision.lower()
        if prec == "int8" or (prec == "auto" and self.deploy_profile != "gpu-pro"):
            order = [f"{stem}.int8.onnx", f"{stem}.fp16.onnx", f"{stem}.onnx"]
        elif prec == "fp16":
            order = [f"{stem}.fp16.onnx", f"{stem}.int8.onnx", f"{stem}.onnx"]
        else:
            order = [f"{stem}.onnx", f"{stem}.fp16.onnx", f"{stem}.int8.onnx"]

        for name in order:
            cand = models_dir / name
            if cand.exists():
                return cand.resolve()
        return None

    def list_quantized_models(self) -> List[Dict[str, Any]]:
        models_dir = Path(settings.models_dir)
        if not models_dir.exists():
            return []
        items: List[Dict[str, Any]] = []
        for p in sorted(models_dir.glob("*.onnx")):
            prec = "int8" if ".int8." in p.name else ("fp16" if ".fp16." in p.name else "fp32")
            items.append(
                {
                    "file": p.name,
                    "precision": prec,
                    "size_mb": round(p.stat().st_size / (1024.0 * 1024.0), 2),
                    "sha256": sha256_digest(p),
                }
            )
        return items


class LowPrecisionOnnxRunner:
    """
    Zero-PyTorch Low-Precision ONNX Runtime Inference Runner shared by `mod-yolov5` and `mod-yolo26`.
    Supports YOLO26 end-to-end no-NMS (`detect`, `pose`, `seg`, `obb`) and YOLOv5 `(1, 25200, 5+nc)`.
    """

    def __init__(self, model_path: Path, default_names: Optional[Dict[int, str]] = None) -> None:
        import onnxruntime as ort  # type: ignore

        self.model_path = Path(model_path).resolve()
        self.default_names = default_names or COCO_NAMES_80
        is_int8 = ".int8." in self.model_path.name.lower()

        avail = ort.get_available_providers()
        providers: List[str] = []
        if "CUDAExecutionProvider" in avail:
            providers.append("CUDAExecutionProvider")
        if "OpenVINOExecutionProvider" in avail:
            providers.append("OpenVINOExecutionProvider")
        if "CoreMLExecutionProvider" in avail and not is_int8:
            providers.append("CoreMLExecutionProvider")
        providers.append("CPUExecutionProvider")

        opts = ort.SessionOptions()
        opts.intra_op_num_threads = precision_manager.cpu_threads
        opts.inter_op_num_threads = 1
        opts.enable_cpu_mem_arena = False
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(str(self.model_path), sess_options=opts, providers=providers)
        inp = self.session.get_inputs()[0]
        self.input_name = inp.name
        self.input_dtype = inp.type
        self.fixed_imgsz = int(inp.shape[2]) if (len(inp.shape) == 4 and isinstance(inp.shape[2], int)) else 640
        self.active_provider = self.session.get_providers()[0]

        meta = self.session.get_modelmeta().custom_metadata_map or {}
        self.names = dict(self.default_names)
        if "names" in meta:
            try:
                parsed = ast.literal_eval(meta["names"])
                if isinstance(parsed, dict):
                    self.names = {int(k): str(v) for k, v in parsed.items()}
                elif isinstance(parsed, list):
                    self.names = {i: str(v) for i, v in enumerate(parsed)}
            except Exception:
                pass
        out0_shape = self.session.get_outputs()[0].shape
        self.is_end2end = str(meta.get("end2end", "")).lower() == "true" or (
            len(out0_shape) == 3 and out0_shape[1] in (100, 300)
        )

    def infer_bgr(
        self, bgr: np.ndarray, conf_thres: float = 0.35, iou_thres: float = 0.45
    ) -> Tuple[List[Dict[str, Any]], int]:
        import cv2  # type: ignore

        h0, w0 = bgr.shape[:2]
        imgsz = self.fixed_imgsz
        r = min(imgsz / max(h0, 1), imgsz / max(w0, 1))
        unpad = (int(round(w0 * r)), int(round(h0 * r)))
        dw = (imgsz - unpad[0]) / 2.0
        dh = (imgsz - unpad[1]) / 2.0
        resized = cv2.resize(bgr, unpad, interpolation=cv2.INTER_LINEAR) if (w0, h0) != unpad else bgr
        padded = cv2.copyMakeBorder(
            resized,
            int(round(dh - 0.1)),
            int(round(dh + 0.1)),
            int(round(dw - 0.1)),
            int(round(dw + 0.1)),
            cv2.BORDER_CONSTANT,
            value=(114, 114, 114),
        )
        rgb = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB)
        blob = np.expand_dims(rgb.transpose(2, 0, 1).astype(np.float32) / 255.0, axis=0)
        if "float16" in self.input_dtype:
            blob = blob.astype(np.float16)

        t0 = time.perf_counter()
        outputs = self.session.run(None, {self.input_name: blob})
        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))

        pred = outputs[0].astype(np.float32)
        pred = pred[0] if pred.ndim == 3 else pred

        def _scale(x1: float, y1: float, x2: float, y2: float) -> List[float]:
            return [
                round(max(0.0, min(float(w0), (float(x1) - dw) / r)), 1),
                round(max(0.0, min(float(h0), (float(y1) - dh) / r)), 1),
                round(max(0.0, min(float(w0), (float(x2) - dw) / r)), 1),
                round(max(0.0, min(float(h0), (float(y2) - dh) / r)), 1),
            ]

        results: List[Dict[str, Any]] = []
        # 1. End-to-end no-NMS (YOLO26): (300, 6+)
        if pred.shape[0] in (100, 300) and 6 <= pred.shape[1] <= 128:
            for row in pred:
                score = float(row[4])
                if score < conf_thres:
                    continue
                cid = int(round(float(row[5])))
                results.append(
                    {
                        "label": self.names.get(cid, f"class_{cid}"),
                        "confidence": round(score, 4),
                        "bbox_xyxy": _scale(row[0], row[1], row[2], row[3]),
                    }
                )
            return results, elapsed_ms

        # 2. Classic YOLOv5: (25200, 5 + nc)
        if pred.shape[0] >= 1000 and pred.shape[1] == len(self.names) + 5:
            cand = pred[pred[:, 4] >= conf_thres]
            if len(cand) == 0:
                return [], elapsed_ms
            probs = cand[:, 5:] * cand[:, 4:5]
            cids = np.argmax(probs, axis=1)
            scores = probs[np.arange(len(cand)), cids]
            keep_m = scores >= conf_thres
            cand, scores, cids = cand[keep_m], scores[keep_m], cids[keep_m]
            if len(cand) == 0:
                return [], elapsed_ms
            half = cand[:, 2:4] / 2.0
            xyxy = np.hstack([cand[:, :2] - half, cand[:, :2] + half])
            keep_idx = _nms(xyxy, scores, iou_thres)
            for idx in keep_idx[:100]:
                cid = int(cids[idx])
                b = xyxy[idx]
                results.append(
                    {
                        "label": self.names.get(cid, f"class_{cid}"),
                        "confidence": round(float(scores[idx]), 4),
                        "bbox_xyxy": _scale(b[0], b[1], b[2], b[3]),
                    }
                )
            return results, elapsed_ms

        # 3. Transposed (4+nc, 8400)
        if pred.shape[0] < pred.shape[1]:
            pred = pred.T
        nc = max(1, len(self.names))
        if pred.shape[1] >= 4 + nc:
            cls_s = pred[:, 4 : 4 + nc]
            cids = np.argmax(cls_s, axis=1)
            scores = cls_s[np.arange(len(pred)), cids]
            m = scores >= conf_thres
            cand, scores, cids = pred[m], scores[m], cids[m]
            if len(cand) == 0:
                return [], elapsed_ms
            half = cand[:, 2:4] / 2.0
            xyxy = np.hstack([cand[:, :2] - half, cand[:, :2] + half])
            keep_idx = _nms(xyxy, scores, iou_thres)
            for idx in keep_idx[:100]:
                cid = int(cids[idx])
                b = xyxy[idx]
                results.append(
                    {
                        "label": self.names.get(cid, f"class_{cid}"),
                        "confidence": round(float(scores[idx]), 4),
                        "bbox_xyxy": _scale(b[0], b[1], b[2], b[3]),
                    }
                )
        return results, elapsed_ms


def _nms(boxes: np.ndarray, scores: np.ndarray, iou_thres: float) -> List[int]:
    if len(boxes) == 0:
        return []
    x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
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
        inter = np.maximum(0.0, xx2 - xx1) * np.maximum(0.0, yy2 - yy1)
        iou = inter / (areas[i] + areas[order[1:]] - inter + 1e-9)
        order = order[np.where(iou <= iou_thres)[0] + 1]
    return keep


precision_manager = PrecisionManager()
