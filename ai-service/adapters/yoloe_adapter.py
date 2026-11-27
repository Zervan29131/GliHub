import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import cv2

from adapters.base import (
    AbstractVisionDetector,
    DetectionBox,
    VisionInferenceOutput,
    render_detections,
    translate_label,
)
from config import settings

# 中文自然语言专项排查词 -> COCO / 工业开放词汇语义映射表（支撑零样本与本地代理协同）
PROMPT_SYNONYM_MAP: Dict[str, str] = {
    "未戴安全帽": "without_helmet",
    "未佩戴安全帽": "without_helmet",
    "不戴安全帽": "without_helmet",
    "安全帽": "With Helmet",
    "头盔": "With Helmet",
    "人员": "person",
    "工人": "person",
    "闯入": "person",
    "手机": "cell phone",
    "玩手机": "cell phone",
    "打电话": "cell phone",
    "车辆": "car",
    "违停": "truck",
    "货车": "truck",
    "化学品瓶": "bottle",
    "敞口桶": "bottle",
    "消火栓": "fire hydrant",
    "背包": "backpack",
    "杂物": "backpack",
}


def parse_prompt_classes(prompt_text: Optional[str]) -> List[str]:
    if not prompt_text or not prompt_text.strip():
        return ["without_helmet", "cell phone", "bottle"]
    parts = [p.strip() for p in re.split(r"[,，;；、\n]+", prompt_text) if p.strip()]
    return parts or [prompt_text.strip()]


class YoloEAdapter(AbstractVisionDetector):
    """
    适配 Ultralytics YOLOE（开放词汇零样本实时检测，支持文本提示词动态设定检测目标）。
    若本地尚未下载 YOLOE 专用开放词汇权重，自动结合本地双模型（安全帽 + COCO 80类）按用户输入提示词进行语义过滤与违章标注，
    并交由第二阶段 VLM 深度验证，确保零样本专项排查开箱即用！
    """

    def __init__(
        self,
        model_code: str,
        weights_path: Optional[Path],
        device: str = "cpu",
        helmet_detector: Optional[AbstractVisionDetector] = None,
        coco_detector: Optional[AbstractVisionDetector] = None,
    ):
        super().__init__(model_code=model_code, weights_path=weights_path, device=device)
        self.helmet_detector = helmet_detector
        self.coco_detector = coco_detector
        self.yoloe_model = None

    @property
    def adapter_type(self) -> str:
        return "yoloe"

    def is_available(self) -> Tuple[bool, str]:
        if not settings.enable_yoloe:
            return False, "已通过 ENABLE_YOLOE=false 关闭"
        try:
            from ultralytics import YOLOE  # noqa: F401
        except Exception:
            return False, "本地未安装 YOLOE 权重（已启用「提示词语义映射 + 本地双模型 + VLM」开放词汇协同模式）"
        if not self.weights_path or not self.weights_path.exists():
            return False, f"本地未缓存 {self.weights_path.name if self.weights_path else 'yoloe.pt'}（启用协同零样本模式）"
        return True, "Ultralytics YOLOE 原生开放词汇引擎就绪"

    def load(self) -> None:
        if self.loaded and self.yoloe_model is not None:
            return
        from ultralytics import YOLOE

        self.yoloe_model = YOLOE(str(self.weights_path))
        self.loaded = True

    def predict(
        self,
        image_path: Path,
        conf_thres: float = 0.25,
        iou_thres: float = 0.45,
        prompt_text: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> VisionInferenceOutput:
        prompts = parse_prompt_classes(prompt_text)
        ok, reason = self.is_available()
        if ok:
            self.load()
            bgr = cv2.imread(str(image_path))
            h, w = bgr.shape[:2]
            t0 = time.perf_counter()
            self.yoloe_model.set_classes(prompts, self.yoloe_model.get_text_pe(prompts))
            results = self.yoloe_model.predict(
                source=str(image_path),
                conf=conf_thres,
                iou=iou_thres,
                device=self.device,
                verbose=False,
            )
            detections: List[DetectionBox] = []
            for r in results:
                for box in r.boxes:
                    cls_id = int(box.cls[0].item())
                    conf = float(box.conf[0].item())
                    label = prompts[cls_id] if 0 <= cls_id < len(prompts) else f"prompt_{cls_id}"
                    detections.append(
                        DetectionBox(
                            label=label,
                            label_zh=f"专项检出:{label}",
                            confidence=round(conf, 4),
                            bbox_xyxy=[float(v) for v in box.xyxy[0].tolist()],
                            is_violation=True,
                            violation_reason=f"命中开放词汇专项排查词: {label}",
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
                has_violation=len(detections) > 0,
                note=f"YOLOE 开放词汇提示词: {', '.join(prompts)}",
            )

        # 协同零样本降级模式：结合提示词语义匹配本地 helmet + coco 80类检测器
        bgr = cv2.imread(str(image_path))
        if bgr is None:
            raise ValueError(f"无法读取图像: {image_path}")
        h, w = bgr.shape[:2]
        t0 = time.perf_counter()

        target_map: Dict[str, str] = {}
        for p in prompts:
            p_low = p.lower()
            mapped = None
            for zh_kw, eng_cls in PROMPT_SYNONYM_MAP.items():
                if zh_kw in p or eng_cls.lower() == p_low:
                    mapped = eng_cls
                    break
            target_map[mapped or p] = p

        merged_dets: List[DetectionBox] = []
        if self.helmet_detector is not None:
            h_out = self.helmet_detector.predict(image_path, conf_thres=conf_thres, iou_thres=iou_thres)
            for d in h_out.detections:
                if d.label in target_map or not prompt_text:
                    user_term = target_map.get(d.label, d.label_zh)
                    merged_dets.append(
                        DetectionBox(
                            label=d.label,
                            label_zh=f"提示词命中:{user_term}",
                            confidence=d.confidence,
                            bbox_xyxy=d.bbox_xyxy,
                            is_violation=(d.label != "With Helmet"),
                            violation_reason=f"专项排查提示词「{user_term}」检出目标",
                        )
                    )
        if self.coco_detector is not None:
            c_out = self.coco_detector.predict(image_path, conf_thres=conf_thres, iou_thres=iou_thres)
            for d in c_out.detections:
                if d.label in target_map:
                    user_term = target_map[d.label]
                    merged_dets.append(
                        DetectionBox(
                            label=d.label,
                            label_zh=f"提示词命中:{user_term}",
                            confidence=d.confidence,
                            bbox_xyxy=d.bbox_xyxy,
                            is_violation=True,
                            violation_reason=f"专项排查提示词「{user_term}」检出目标",
                        )
                    )

        elapsed_ms = max(1, int(round((time.perf_counter() - t0) * 1000)))
        out_dir = output_dir or Path(settings.output_dir)
        saved_path, saved_url = render_detections(bgr, merged_dets, out_dir, prefix=self.model_code)
        return VisionInferenceOutput(
            model_code=self.model_code,
            adapter_type=self.adapter_type,
            device=self.device,
            inference_ms=elapsed_ms,
            image_width=w,
            image_height=h,
            annotated_image_path=str(saved_path),
            annotated_image_url=saved_url,
            detections=merged_dets,
            has_violation=any(d.is_violation for d in merged_dets),
            fallback_used=True,
            note=f"{reason} | 生效提示词: {', '.join(prompts)}",
        )
