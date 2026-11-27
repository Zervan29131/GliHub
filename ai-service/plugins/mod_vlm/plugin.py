from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from adapters.base import DetectionBox
from config import settings
from core.plugin_registry import BaseAiPlugin
from vlm.reviewer import VlmReviewResult, vlm_reviewer


class VlmReviewPlugin(BaseAiPlugin):
    """Plugin 5 (`mod-vlm`): Multimodal visual secondary verifier (Q4_K_M local / OpenAI-compatible API)."""

    def check_readiness(self) -> tuple[bool, str]:
        if settings.vlm_api_key:
            return True, f"已配置多模态 API ({settings.vlm_model})"
        return True, f"支持本地 GGUF Q4_K_M ({settings.vlm_base_url}) + 内置 EHS 规则引擎双模兜底"

    def runtime_metadata(self) -> Dict[str, Any]:
        return {
            "vlm_base_url": settings.vlm_base_url,
            "vlm_model": settings.vlm_model,
            "quantization_recommended": "GGUF Q4_K_M (qwen3-vl:4b / internvl3:8b)",
        }

    async def review(
        self,
        image_path: Path,
        detections: List[DetectionBox],
        place_type: str = "production",
        area_name: str = "现场作业区",
        hazard_context: Optional[str] = None,
        prompt_text: Optional[str] = None,
    ) -> VlmReviewResult:
        return await vlm_reviewer.review(
            image_path=image_path,
            detections=detections,
            place_type=place_type,
            area_name=area_name,
            hazard_context=hazard_context,
            prompt_text=prompt_text,
        )
