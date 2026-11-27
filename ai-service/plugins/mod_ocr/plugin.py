from __future__ import annotations

import base64
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

from config import settings
from core.plugin_registry import BaseAiPlugin
from rag.parser import extract_text_from_file, split_legal_clauses


class OcrDocumentPlugin(BaseAiPlugin):
    """
    Plugin 7 (`mod-ocr`):
    Multi-tier document & certificate parser:
      1. DeepSeek-OCR 2 / PaddleOCR-VL OpenAI-compatible Vision API (if `OCR_API_BASE_URL` set)
      2. Local RapidOCR / PP-OCRv4 ONNX INT8 CPU engine (if `rapidocr_onnxruntime` installed)
      3. Built-in `pypdf` + structured GB/Safety-Law clause splitter (zero extra dependency)
    """

    def __init__(self, manifest: Dict[str, Any]) -> None:
        super().__init__(manifest)
        self._rapid_ocr: Any = None

    def _get_rapid_ocr(self) -> Any:
        if self._rapid_ocr is None:
            try:
                from rapidocr_onnxruntime import RapidOCR  # type: ignore

                self._rapid_ocr = RapidOCR()
            except ImportError:
                self._rapid_ocr = False
        return self._rapid_ocr if self._rapid_ocr is not False else None

    def check_readiness(self) -> tuple[bool, str]:
        if settings.ocr_api_base_url:
            return True, f"已连接远端 VL-OCR ({settings.ocr_model})"
        if self._get_rapid_ocr() is not None:
            return True, "本地 PP-OCRv4 ONNX INT8 引擎就绪"
        return True, "轻量 PDF/文本法规条款结构化解析器就绪"

    def runtime_metadata(self) -> Dict[str, Any]:
        return {
            "ocr_api_configured": bool(settings.ocr_api_base_url),
            "rapidocr_int8_installed": self._get_rapid_ocr() is not None,
        }

    async def parse_file(
        self, file_path: Path, applicable_places: str = "production,storage,auxiliary"
    ) -> Dict[str, Any]:
        suffix = file_path.suffix.lower()
        engine_used = "pypdf_clause_splitter"
        extracted_text = ""

        # Image ticket / scanned certificate path
        if suffix in (".jpg", ".jpeg", ".png", ".bmp", ".webp"):
            if settings.ocr_api_base_url and settings.ocr_api_key:
                try:
                    b64 = base64.b64encode(file_path.read_bytes()).decode("ascii")
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {settings.ocr_api_key}",
                    }
                    payload = {
                        "model": settings.ocr_model,
                        "messages": [
                            {
                                "role": "user",
                                "content": [
                                    {"type": "text", "text": "请完整提取图中所有法规条文、检验结论或SDS理化参数，保持Markdown段落与表格结构。"},
                                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                                ],
                            }
                        ],
                    }
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        r = await client.post(
                            f"{settings.ocr_api_base_url.rstrip('/')}/chat/completions",
                            headers=headers,
                            json=payload,
                        )
                        r.raise_for_status()
                        extracted_text = r.json()["choices"][0]["message"]["content"]
                        engine_used = f"vl_ocr:{settings.ocr_model}"
                except Exception:
                    pass

            if not extracted_text:
                ocr = self._get_rapid_ocr()
                if ocr is not None:
                    res, _ = ocr(str(file_path))
                    if res:
                        extracted_text = "\n".join(str(line[1]) for line in res)
                        engine_used = "rapidocr_ppocrv4_int8"

        if not extracted_text:
            extracted_text = extract_text_from_file(file_path)
            engine_used = "pypdf_parser" if suffix == ".pdf" else "utf8_text_parser"

        clauses = split_legal_clauses(extracted_text, applicable_places=applicable_places)
        return {
            "file_name": file_path.name,
            "ocr_engine": engine_used,
            "char_count": len(extracted_text),
            "chunk_count": len(clauses),
            "raw_text_preview": extracted_text[:800],
            "clauses": clauses,
        }
