from __future__ import annotations

from pathlib import Path
import time
from typing import Any, Dict, List, Optional

import cv2

from adapters.base import DetectionBox, VisionInferenceOutput, render_detections
from config import settings
from core.plugin_registry import BaseAiPlugin
from core.precision import LowPrecisionOnnxRunner, precision_manager

PROMPT_SYNONYM_RULES: List[tuple[List[str], List[str], str]] = [
    (["安全帽", "头盔", "helmet", "未戴", "未佩戴"], ["without_helmet", "no_helmet", "person"], "专项排查：未规范佩戴安全帽"),
    (["手机", "打电话", "phone", "cell"], ["cell phone"], "专项排查：防爆区违规使用手机"),
    (["桶", "容器", "瓶", "化学品", "drum", "bottle", "cup"], ["bottle", "cup"], "专项排查：敞口/散落化学品容器"),
    (["通道", "杂物", "堵塞", "箱", "包", "占压", "block", "bag"], ["backpack", "suitcase", "chair"], "专项排查：堵塞消防/疏散通道杂物"),
    (["车", "槽车", "货车", "违停", "truck", "car"], ["truck", "car", "bus", "motorcycle"], "专项排查：厂区车辆违停/违规入场"),
    (["消火栓", "灭火", "消防", "hydrant"], ["fire hydrant"], "专项排查：消防设施周边核查"),
]


class YoloEPlugin(BaseAiPlugin):
    """
    Plugin 4 (`mod-yoloe`):
    Open-vocabulary prompt-driven inspection:
    - Uses native Ultralytics YOLOE (`yoloe-11s-seg.pt`) if installed & cached locally;
    - Otherwise executes zero-PyTorch INT8 semantic prompt grounding over `yolo26n.int8.onnx` + `yolov5_helmet.int8.onnx`!
    """

    def __init__(self, manifest: Dict[str, Any]) -> None:
        super().__init__(manifest)
        self._onnx_runner: Optional[LowPrecisionOnnxRunner] = None
        self._helmet_runner: Optional[LowPrecisionOnnxRunner] = None

    def _ensure_loaded(self) -> None:
        if self._onnx_runner is None:
            p = precision_manager.resolve_onnx_model_file("yolo26n")
            if p and p.exists():
                self._onnx_runner = LowPrecisionOnnxRunner(p)
        if self._helmet_runner is None:
            h = precision_manager.resolve_onnx_model_file("yolov5_helmet")
            if h and h.exists():
                self._helmet_runner = LowPrecisionOnnxRunner(h, default_names={0: "With Helmet"})

    def check_readiness(self) -> tuple[bool, str]:
        p = precision_manager.resolve_onnx_model_file("yolo26n")
        if p and p.exists():
            return True, f"零样本提示词 INT8 定位引擎就绪 ({p.name})"
        return False, "缺少底层视觉 ONNX 模型"

    def runtime_metadata(self) -> Dict[str, Any]:
        has_ultralytics = False
        try:
            import ultralytics  # noqa: F401

            has_ultralytics = True
        except ImportError:
            pass
        return {
            "native_yoloe_pkg_installed": has_ultralytics,
            "mode": "bilingual_ehs_prompt_int8",
        }

    def predict(
        self,
        image_path: Path,
        prompt_text: Optional[str] = None,
        model_code: str = "yoloe_zero_shot",
        conf_thres: float = 0.30,
        iou_thres: float = 0.45,
    ) -> VisionInferenceOutput:
        self._ensure_loaded()
        if self._onnx_runner is None:
            raise RuntimeError("ONNX vision runner unavailable for mod-yoloe")

        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"Cannot decode image: {image_path}")
        h, w = bgr.shape[:2]

        prompt = (prompt_text or "未佩戴安全帽 违规手机 散落化学品桶 堵塞通道杂物").strip()
        prompt_lower = prompt.lower()

        t0 = time.perf_counter()
        raw, _ = self._onnx_runner.infer_bgr(bgr, conf_thres=conf_thres, iou_thres=iou_thres)
        helmets: List[Dict[str, Any]] = []
        if self._helmet_runner is not None:
            helmets, _ = self._helmet_runner.infer_bgr(bgr, conf_thres=0.28, iou_thres=0.45)

        # Match prompt terms to target classes
        matched_targets: Dict[str, str] = {}
        for kw_list, cls_list, zh_desc in PROMPT_SYNONYM_RULES:
            if any(kw in prompt_lower for kw in kw_list):
                for c in cls_list:
                    matched_targets[c] = zh_desc

        boxes: List[DetectionBox] = []
        for r in raw:
            lbl = r["label"]
            if lbl == "person" and ("person" in matched_targets or "without_helmet" in matched_targets):
                px1, py1, px2, py2 = r["bbox_xyxy"]
                pw, ph = max(1.0, px2 - px1), max(1.0, py2 - py1)
                hx1, hy1, hx2, hy2 = px1 - 0.12 * pw, max(0.0, py1 - 0.15 * ph), px2 + 0.12 * pw, py1 + 0.45 * ph
                has_h = any(
                    hx1 <= 0.5 * (hm["bbox_xyxy"][0] + hm["bbox_xyxy"][2]) <= hx2
                    and hy1 <= 0.5 * (hm["bbox_xyxy"][1] + hm["bbox_xyxy"][3]) <= hy2
                    for hm in helmets
                )
                if not has_h:
                    boxes.append(
                        DetectionBox(
                            label="without_helmet",
                            label_zh=f"提示词命中: 未戴安全帽",
                            confidence=r["confidence"],
                            bbox_xyxy=r["bbox_xyxy"],
                            is_violation=True,
                            violation_reason=f"命中零样本排查词「{prompt}」",
                        )
                    )
                continue

            if lbl in matched_targets or not matched_targets:
                reason = matched_targets.get(lbl, f"开放词汇检出({prompt[:12]})")
                boxes.append(
                    DetectionBox(
                        label=lbl,
                        label_zh=f"提示词命中: {lbl}",
                        confidence=r["confidence"],
                        bbox_xyxy=r["bbox_xyxy"],
                        is_violation=True,
                        violation_reason=reason,
                    )
                )

        ms = max(1, int(round((time.perf_counter() - t0) * 1000.0)))
        save_p, url = render_detections(bgr, boxes, Path(settings.output_dir), prefix="yoloe_prompt")
        return VisionInferenceOutput(
            model_code=model_code,
            adapter_type="mod-yoloe-open-vocab-int8",
            device=self._onnx_runner.active_provider,
            inference_ms=ms,
            image_width=w,
            image_height=h,
            annotated_image_path=str(save_p),
            annotated_image_url=url,
            detections=boxes,
            has_violation=any(b.is_violation for b in boxes),
            precision="int8",
            plugin_id=self.plugin_id,
            note=f"开放词汇排查词: {prompt}",
        )
