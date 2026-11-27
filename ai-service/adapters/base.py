from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional, Tuple
import uuid
import cv2
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
    note: Optional[str] = None


LABEL_ZH_MAP = {
    "With Helmet": "已佩戴安全帽",
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
    "bottle": "散落容器/化学品瓶",
    "backpack": "随身携行包",
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
    ]
    for fp in font_candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, size=size)
            except Exception:
                continue
    return ImageFont.load_default()


def render_detections(
    bgr_image: np.ndarray,
    detections: List[DetectionBox],
    output_dir: Path,
    prefix: str = "det",
) -> Tuple[Path, str]:
    """在原图上绘制合规框(绿/蓝)与违章告警框(红)，保存并返回本地路径与静态相对URL."""
    output_dir.mkdir(parents=True, exist_ok=True)
    rgb = cv2.cvtColor(bgr_image, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(rgb)
    draw = ImageDraw.Draw(pil_img)
    font = _load_cjk_font(18)

    for det in detections:
        x1, y1, x2, y2 = [int(round(v)) for v in det.bbox_xyxy]
        color = (229, 57, 53) if det.is_violation else (46, 125, 50)
        draw.rectangle([x1, y1, x2, y2], outline=color, width=3)
        caption = f"{det.label_zh} {det.confidence:.2f}"
        bbox_txt = draw.textbbox((x1, max(0, y1 - 24)), caption, font=font)
        pad_box = [
            bbox_txt[0] - 2,
            bbox_txt[1] - 2,
            bbox_txt[2] + 4,
            bbox_txt[3] + 2,
        ]
        draw.rectangle(pad_box, fill=color)
        draw.text((x1 + 1, max(0, y1 - 24)), caption, fill=(255, 255, 255), font=font)

    filename = f"{prefix}_{uuid.uuid4().hex[:10]}.jpg"
    save_path = output_dir / filename
    pil_img.save(save_path, format="JPEG", quality=92)
    return save_path, f"/outputs/{filename}"


class AbstractVisionDetector(ABC):
    def __init__(self, model_code: str, weights_path: Optional[Path], device: str = "cpu"):
        self.model_code = model_code
        self.weights_path = weights_path
        self.device = device
        self.loaded = False

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def is_available(self) -> Tuple[bool, str]:
        raise NotImplementedError

    @abstractmethod
    def load(self) -> None:
        raise NotImplementedError

    @abstractmethod
    def predict(
        self,
        image_path: Path,
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
        prompt_text: Optional[str] = None,
        output_dir: Optional[Path] = None,
    ) -> VisionInferenceOutput:
        raise NotImplementedError
