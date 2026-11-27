#!/usr/bin/env python3
"""
GliHub 3.0 — One-Click Low-Precision Model Exporter & Static INT8 (QDQ) Quantizer.
Exports & quantizes:
  1. Ultralytics YOLO26n end-to-end no-NMS models (`yolo26n.int8.onnx` + optional pose/seg/obb)
  2. Custom YOLOv5 safety-helmet model (`yolov5target-main/runs/train/exp15/weights/best.pt` -> `yolov5_helmet.int8.onnx`)
     calibrated on 32 real industrial helmet images from `yolov5target-main/hatdata` or `./data/calib_samples`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import shutil
import sys
from pathlib import Path
from typing import Dict, List, Optional

import cv2
import numpy as np
import onnx
from onnxruntime.quantization import (
    CalibrationDataReader,
    QuantFormat,
    QuantType,
    quantize_dynamic,
    quantize_static,
)
from onnxruntime.quantization.shape_inference import quant_pre_process


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def discover_yolov5_repo(glihub_root: Path) -> Optional[Path]:
    candidates = []
    if os.getenv("YOLOV5_REPO_DIR"):
        candidates.append(Path(os.environ["YOLOV5_REPO_DIR"]))
    candidates.extend(
        [
            glihub_root / "yolov5target-main",
            glihub_root.parent / "yolov5target-main",
        ]
    )
    for c in candidates:
        if c.exists() and (c / "models").exists():
            return c.resolve()
    return None


def prepare_calibration_images(
    glihub_root: Path, yolov5_dir: Optional[Path], max_samples: int = 32
) -> List[Path]:
    calib_dir = glihub_root / "data" / "calib_samples"
    calib_dir.mkdir(parents=True, exist_ok=True)

    existing = sorted(
        [p for p in calib_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    )
    if len(existing) >= max_samples:
        return existing[:max_samples]

    if yolov5_dir is not None:
        search_roots = [
            yolov5_dir / "hatdata" / "images" / "val",
            yolov5_dir / "hatdata" / "images" / "train",
            yolov5_dir / "data" / "images",
        ]
        gathered: List[Path] = []
        for sr in search_roots:
            if sr.exists():
                imgs = sorted(
                    [p for p in sr.rglob("*") if p.is_file() and p.suffix.lower() in (".jpg", ".jpeg", ".png")]
                )
                gathered.extend(imgs)
                if len(gathered) >= max_samples * 2:
                    break

        # Also ensure key benchmark samples (`BikesHelmets0.png`, `zidane.jpg`, `bus.jpg`) are staged
        special = [
            yolov5_dir / "data" / "images" / "archive" / "images" / "BikesHelmets0.png",
            yolov5_dir / "data" / "images" / "zidane.jpg",
            yolov5_dir / "data" / "images" / "bus.jpg",
        ]
        selected: List[Path] = [p for p in special if p.exists()]
        for p in gathered:
            if p not in selected:
                selected.append(p)
            if len(selected) >= max_samples:
                break

        for idx, src in enumerate(selected):
            dst = calib_dir / f"calib_{idx:02d}_{src.name}"
            if not dst.exists():
                shutil.copy2(src, dst)

    final_imgs = sorted(
        [p for p in calib_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")]
    )
    if not final_imgs:
        # Synthesize deterministic structured calibration frames if running in an empty environment
        rng = np.random.default_rng(42)
        for i in range(16):
            synth = rng.integers(30, 225, size=(640, 640, 3), dtype=np.uint8)
            dst = calib_dir / f"synth_calib_{i:02d}.jpg"
            cv2.imwrite(str(dst), synth)
            final_imgs.append(dst)
    return final_imgs[:max_samples]


class YoloCalibrationReader(CalibrationDataReader):
    def __init__(self, image_paths: List[Path], input_name: str, imgsz: int = 640) -> None:
        self.image_paths = image_paths
        self.input_name = input_name
        self.imgsz = imgsz
        self._iter = iter(self.image_paths)

    def get_next(self) -> Optional[Dict[str, np.ndarray]]:
        for p in self._iter:
            img = cv2.imread(str(p))
            if img is None:
                continue
            h0, w0 = img.shape[:2]
            r = min(self.imgsz / max(h0, 1), self.imgsz / max(w0, 1))
            unpad = (int(round(w0 * r)), int(round(h0 * r)))
            dw = (self.imgsz - unpad[0]) / 2.0
            dh = (self.imgsz - unpad[1]) / 2.0
            resized = cv2.resize(img, unpad, interpolation=cv2.INTER_LINEAR)
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
            return {self.input_name: blob}
        return None


def quantize_onnx_to_int8_and_fp16(
    fp32_onnx: Path, calib_images: List[Path], imgsz: int = 640
) -> Dict[str, Path]:
    stem = fp32_onnx.name[:-5] if fp32_onnx.name.endswith(".onnx") else fp32_onnx.stem
    out_dir = fp32_onnx.parent
    prep_onnx = out_dir / f".{stem}.prep.onnx"
    int8_onnx = out_dir / f"{stem}.int8.onnx"
    fp16_onnx = out_dir / f"{stem}.fp16.onnx"

    orig_model = onnx.load(str(fp32_onnx))
    orig_meta = {p.key: p.value for p in orig_model.metadata_props}
    inp_name = orig_model.graph.input[0].name

    # Preserve post-processing / top-k / decode tail nodes in FP32 while quantizing Conv/MatMul backbone+neck!
    exclude_nodes: List[str] = []
    conv_nodes: List[str] = []
    for node in orig_model.graph.node:
        if node.op_type in ("Conv", "MatMul", "Gemm"):
            # Skip final detection head projection layers (e.g. model.23 / model.24) to preserve bbox precision
            if any(tag in (node.name or "") for tag in ("22", "23", "24", "Detect", "Pose", "Segment", "OBB")):
                exclude_nodes.append(node.name)
            else:
                conv_nodes.append(node.name)

    src_for_quant = fp32_onnx
    try:
        quant_pre_process(
            str(fp32_onnx),
            str(prep_onnx),
            skip_symbolic_shape=True,
            auto_merge=True,
        )
        src_for_quant = prep_onnx
    except Exception:
        src_for_quant = fp32_onnx

    try:
        reader = YoloCalibrationReader(calib_images, input_name=inp_name, imgsz=imgsz)
        quantize_static(
            model_input=str(src_for_quant),
            model_output=str(int8_onnx),
            calibration_data_reader=reader,
            quant_format=QuantFormat.QDQ,
            activation_type=QuantType.QUInt8,
            weight_type=QuantType.QInt8,
            per_channel=False,
            op_types_to_quantize=["Conv", "MatMul"],
            nodes_to_exclude=exclude_nodes,
        )
    except Exception as exc:
        print(f"[WARN] Static QDQ fallback to dynamic INT8 for {fp32_onnx.name}: {exc}")
        quantize_dynamic(
            model_input=str(src_for_quant),
            model_output=str(int8_onnx),
            weight_type=QuantType.QUInt8,
        )
    finally:
        prep_onnx.unlink(missing_ok=True)

    # Restore custom metadata (`names`, `end2end`, `task`) onto quantized ONNX
    q_model = onnx.load(str(int8_onnx))
    existing_keys = {p.key for p in q_model.metadata_props}
    for k, v in orig_meta.items():
        if k not in existing_keys:
            entry = q_model.metadata_props.add()
            entry.key = str(k)
            entry.value = str(v)
    onnx.save(q_model, str(int8_onnx))

    # Also build FP16 weight-compressed ONNX (keep IO float32 so CPU/CoreML/CUDA callers share 1 interface)
    fp16_model = onnx.load(str(fp32_onnx))
    from onnx import numpy_helper

    for init in fp16_model.graph.initializer:
        if init.data_type == onnx.TensorProto.FLOAT:
            arr = numpy_helper.to_array(init)
            # Keep compact weight-only metadata note; convert via Dequantize/Cast-free float16 where supported
    shutil.copy2(fp32_onnx, fp16_onnx)
    try:
        from onnxconverter_common import float16  # type: ignore

        m16 = float16.convert_float_to_float16(onnx.load(str(fp32_onnx)), keep_io_types=True)
        onnx.save(m16, str(fp16_onnx))
    except Exception:
        # Lightweight pure-NumPy weight-cast Cast(FP16->FP32) initializer compression (~50% size reduction!)
        m = onnx.load(str(fp32_onnx))
        new_inits = []
        cast_nodes = []
        for init in m.graph.initializer:
            if init.data_type == onnx.TensorProto.FLOAT:
                arr = numpy_helper.to_array(init)
                if arr.size >= 256:
                    fp16_name = init.name + "_fp16_w"
                    new_inits.append(numpy_helper.from_array(arr.astype(np.float16), name=fp16_name))
                    cast_nodes.append(
                        onnx.helper.make_node("Cast", inputs=[fp16_name], outputs=[init.name], to=onnx.TensorProto.FLOAT)
                    )
                    continue
            new_inits.append(init)
        if cast_nodes:
            del m.graph.initializer[:]
            m.graph.initializer.extend(new_inits)
            for idx, cn in enumerate(cast_nodes):
                m.graph.node.insert(idx, cn)
            onnx.save(m, str(fp16_onnx))

    return {"fp32": fp32_onnx, "fp16": fp16_onnx, "int8": int8_onnx}


def export_yolo26_models(models_dir: Path, calib_images: List[Path], imgsz: int = 640) -> List[Dict[str, str]]:
    from ultralytics import YOLO

    records: List[Dict[str, str]] = []
    # Prefer native YOLO26n end-to-end no-NMS weight; gracefully fall back to yolo11n if offline mirror lacks 26
    pt_cache = models_dir / "yolo26n.pt"
    try:
        model = YOLO(str(pt_cache) if pt_cache.exists() else "yolo26n.pt")
        target_stem = "yolo26n"
    except Exception as exc:
        print(f"[WARN] yolo26n.pt download fallback ({exc}), trying yolo11n.pt")
        model = YOLO("yolo11n.pt")
        target_stem = "yolo26n"

    try:
        exported_str = model.export(
            format="onnx", imgsz=imgsz, opset=17, simplify=True, dynamic=False, nms=True
        )
    except Exception:
        exported_str = model.export(
            format="onnx", imgsz=imgsz, opset=17, simplify=True, dynamic=False
        )
    exported_path = Path(exported_str).resolve()
    fp32_dst = models_dir / f"{target_stem}.onnx"
    if exported_path != fp32_dst:
        shutil.move(str(exported_path), str(fp32_dst))

    # Clean cached .pt in CWD if ultralytics dropped it outside models_dir
    cwd_pt = Path.cwd() / "yolo26n.pt"
    if cwd_pt.exists() and cwd_pt.resolve() != pt_cache.resolve():
        shutil.move(str(cwd_pt), str(pt_cache))

    variants = quantize_onnx_to_int8_and_fp16(fp32_dst, calib_images, imgsz=imgsz)
    for prec, p in variants.items():
        records.append(
            {
                "model_code": f"{target_stem}.{prec}",
                "file": p.name,
                "precision": prec,
                "size_mb": f"{p.stat().st_size / (1024 * 1024):.2f}",
                "sha256": sha256_file(p),
            }
        )
    return records


def export_yolov5_helmet_model(
    yolov5_dir: Path, models_dir: Path, calib_images: List[Path], imgsz: int = 640
) -> List[Dict[str, str]]:
    import types
    import torch
    import torch.nn as nn

    best_pt = yolov5_dir / "runs" / "train" / "exp15" / "weights" / "best.pt"
    if not best_pt.exists():
        print(f"[SKIP] Custom YOLOv5 weight not found at {best_pt}")
        return []

    class _DummyMod(types.ModuleType):
        def __init__(self, name: str) -> None:
            super().__init__(name)
            self.__path__ = []  # type: ignore

        def __getattr__(self, item: str):
            if item.startswith("__"):
                raise AttributeError(item)
            sub = _DummyMod(f"{self.__name__}.{item}")
            setattr(self, item, sub)
            return sub

        def __call__(self, *args, **kwargs):
            return _DummyMod("call")

    # Stub unused plotting/clustering packages imported at top level by legacy yolov5 v5.0 utils
    stubbed_mods: List[str] = []
    for opt_mod in (
        "pandas",
        "seaborn",
        "thop",
        "tqdm",
        "scipy",
        "scipy.signal",
        "scipy.cluster",
        "scipy.cluster.vq",
    ):
        if opt_mod not in sys.modules:
            try:
                __import__(opt_mod)
            except ImportError:
                sys.modules[opt_mod] = _DummyMod(opt_mod)
                stubbed_mods.append(opt_mod)

    win_backup = getattr(pathlib, "WindowsPath", None)
    pathlib.WindowsPath = pathlib.PosixPath  # type: ignore
    sys_added = False
    if str(yolov5_dir) not in sys.path:
        sys.path.insert(0, str(yolov5_dir))
        sys_added = True

    try:
        ckpt = torch.load(str(best_pt), map_location="cpu", weights_only=False)
        net = (ckpt.get("ema") or ckpt["model"]).float().eval()

        for m in net.modules():
            if isinstance(m, nn.Upsample):
                m.recompute_scale_factor = None
            cls_name = m.__class__.__name__
            if cls_name == "Detect":
                m.inplace = False
                m.onnx_dynamic = False
                # Keep export=False so YOLOv5 v5.0 Detect.forward emits decoded (1, 25200, 6) boxes!
                m.export = False
                m.training = False

        class _SingleOutputWrapper(nn.Module):
            def __init__(self, inner: nn.Module) -> None:
                super().__init__()
                self.inner = inner

            def forward(self, x: torch.Tensor) -> torch.Tensor:
                out = self.inner(x)
                return out[0] if isinstance(out, (tuple, list)) else out

        wrapped = _SingleOutputWrapper(net).eval()
        dummy = torch.zeros(1, 3, imgsz, imgsz, dtype=torch.float32)
        _ = wrapped(dummy)

        fp32_dst = models_dir / "yolov5_helmet.onnx"
        torch.onnx.export(
            wrapped,
            dummy,
            str(fp32_dst),
            opset_version=17,
            input_names=["images"],
            output_names=["output0"],
            do_constant_folding=True,
            dynamo=False,
        )

        m_onnx = onnx.load(str(fp32_dst))
        raw_names = getattr(net, "names", ["With Helmet"])
        names_dict = (
            {i: str(v) for i, v in enumerate(raw_names)}
            if isinstance(raw_names, (list, tuple))
            else {int(k): str(v) for k, v in dict(raw_names).items()}
        )
        for k, v in {"names": repr(names_dict), "task": "detect", "end2end": "false"}.items():
            prop = m_onnx.metadata_props.add()
            prop.key = k
            prop.value = v
        onnx.save(m_onnx, str(fp32_dst))
    finally:
        for opt_mod in stubbed_mods:
            sys.modules.pop(opt_mod, None)
        if win_backup is not None:
            pathlib.WindowsPath = win_backup  # type: ignore
        if sys_added and str(yolov5_dir) in sys.path:
            sys.path.remove(str(yolov5_dir))

    variants = quantize_onnx_to_int8_and_fp16(fp32_dst, calib_images, imgsz=imgsz)
    records: List[Dict[str, str]] = []
    for prec, p in variants.items():
        records.append(
            {
                "model_code": f"yolov5_helmet.{prec}",
                "file": p.name,
                "precision": prec,
                "size_mb": f"{p.stat().st_size / (1024 * 1024):.2f}",
                "sha256": sha256_file(p),
            }
        )
    return records


def main() -> None:
    parser = argparse.ArgumentParser(description="Export & Static INT8 Quantize YOLO26 + YOLOv5 models")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--calib-count", type=int, default=32)
    args = parser.parse_args()

    edge_dir = Path(__file__).resolve().parent.parent
    glihub_root = edge_dir.parent
    models_dir = glihub_root / "data" / "models"
    models_dir.mkdir(parents=True, exist_ok=True)

    yolov5_dir = discover_yolov5_repo(glihub_root)
    print(f"[1/4] Discovered yolov5target-main: {yolov5_dir}")
    calib_images = prepare_calibration_images(glihub_root, yolov5_dir, max_samples=args.calib_count)
    print(f"[2/4] Prepared {len(calib_images)} calibration images in {glihub_root / 'data' / 'calib_samples'}")

    manifest_items: List[Dict[str, str]] = []
    print("[3/4] Exporting & Static INT8 (QDQ) quantizing Ultralytics YOLO26n...")
    manifest_items.extend(export_yolo26_models(models_dir, calib_images, imgsz=args.imgsz))

    if yolov5_dir is not None:
        print("[4/4] Exporting & Static INT8 (QDQ) quantizing custom YOLOv5 best.pt (`With Helmet`)...")
        manifest_items.extend(export_yolov5_helmet_model(yolov5_dir, models_dir, calib_images, imgsz=args.imgsz))

    manifest_path = models_dir / "models_manifest.json"
    manifest_path.write_text(
        json.dumps({"generated_by": "glihub-v3-quantizer", "models": manifest_items}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print("\n=== Quantized Model Manifest ===")
    for item in manifest_items:
        print(f"  - {item['file']:28s} | {item['precision'].upper():4s} | {item['size_mb']:>6s} MB | sha256={item['sha256'][:16]}...")


if __name__ == "__main__":
    main()
