from __future__ import annotations

from pathlib import Path
from typing import List, Optional, Tuple, Union
import uuid
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel, Field


class DetectionBox(BaseModel):
    label: str
    label_zh: str
    confidence: float
    bbox_xyxy: List[float] = Field(description="[x1, y1, x2, y2] in pixel coordinates")
    is_violation: bool = False
    violation_reason: Optional[str] = None


class VisionInferenceOutput(BaseModel):
    model_code: str
    adapter_type: str
    device: str
    inference_ms: int
    image_width: int
    image_height: int
    annotated_image_path: str
    annotated_image_url: str
    detections: List[DetectionBox] = Field(default_factory=list)
    has_violation: bool = False
    fallback_used: bool = False
    precision: str = "int8"
    plugin_id: Optional[str] = None
    note: Optional[str] = None


LABEL_ZH_MAP = {
    "With Helmet": "已佩戴安全帽",
    "with_helmet": "已佩戴安全帽",
    "without_helmet": "未佩戴安全帽(违章)",
    "no_helmet": "未佩戴安全帽(违章)",
    "helmet": "已佩戴安全帽",
    "person": "作业人员",
    "cell phone": "违规使用手机",
    "car": "厂区车辆",
    "truck": "危化运输货车",
    "bus": "厂区通勤车",
    "motorcycle": "机动二轮车",
    "bicycle": "非机动车",
    "fire hydrant": "消火栓设施",
    "bottle": "散落容器/化学品桶",
    "cup": "敞口容器",
    "backpack": "通道堆放杂物/携行包",
    "suitcase": "堵塞通道箱体",
    "chair": "占道杂物",
    "smoke": "异常烟雾(险情)",
    "fire": "明火告警(险情)",
    "leakage": "跑冒滴漏异常",
}


def translate_label(label: str) -> str:
    return LABEL_ZH_MAP.get(label, label)


def _load_cjk_font(size: int = 18):
    font_candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "C:/Windows/Fonts/msyh.ttc",
    ]
    for fp in font_candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_detections(
    image_input: Union[np.ndarray, Image.Image, Path],
    detections: List[DetectionBox],
    output_dir: Path,
    prefix: str = "det",
) -> Tuple[Path, str]:
    """Pure Pillow-compatible annotator so 0-plugin mode works even without OpenCV installed."""
    output_dir.mkdir(parents=True, exist_ok=True)
    if isinstance(image_input, Path):
        pil_img = Image.open(image_input).convert("RGB")
    elif isinstance(image_input, Image.Image):
        pil_img = image_input.convert("RGB")
    else:
        # BGR ndarray from OpenCV -> RGB
        rgb = image_input[..., ::-1].copy()
        pil_img = Image.fromarray(rgb)

    draw = ImageDraw.Draw(pil_img)
    font = _load_cjk_font(18)

    for det in detections:
        x1, y1, x2, y2 = [int(round(v)) for v in det.bbox_xyxy]
        color = (229, 57, 53) if det.is_violation else (46, 125, 50)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        caption = f"{det.label_zh} {det.confidence:.2f}"
        bbox_txt = draw.textbbox((x1, max(0, y1 - 24)), caption, font=font)
        pad_box = [bbox_txt[0] - 2, bbox_txt[1] - 2, bbox_txt[2] + 4, bbox_txt[3] + 2]
        draw.rectangle(pad_box, fill=color)
        draw.text((x1 + 1, max(0, y1 - 24)), caption, fill=(255, 255, 255), font=font)

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.jpg"
    save_path = output_dir / filename
    pil_img.save(save_path, format="JPEG", quality=90)
    return save_path, f"/outputs/{filename}"
