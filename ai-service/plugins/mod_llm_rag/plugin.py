from __future__ import annotations

from typing import Any, Dict

from config import settings
from core.plugin_registry import BaseAiPlugin
from rag.retriever import rag_engine


class LlmRagPlugin(BaseAiPlugin):
    """Plugin 6 (`mod-llm-rag`): DeepSeek/Qwen Safety Brain + PostgreSQL pgvector Hybrid RAG."""

    def check_readiness(self) -> tuple[bool, str]:
        pgvec = rag_engine.has_pgvector()
        mode = "pgvector 原生向量索引" if pgvec else "PostgreSQL JSONB 混合余弦检索"
        return True, f"{mode} · 模型 {settings.llm_model}"

    def runtime_metadata(self) -> Dict[str, Any]:
        return {
            "llm_base_url": settings.llm_base_url,
            "llm_model": settings.llm_model,
            "embedding_model": settings.embedding_model,
            "pgvector_enabled": rag_engine.has_pgvector(),
        }
