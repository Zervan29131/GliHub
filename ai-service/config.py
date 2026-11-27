from __future__ import annotations

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent
GLIHUB_ROOT = BASE_DIR.parent


def _discover_yolov5_dir() -> str:
    env_val = os.getenv("YOLOV5_REPO_DIR")
    candidates = []
    if env_val:
        candidates.append(Path(env_val))
    candidates.extend(
        [
            GLIHUB_ROOT / "yolov5target-main",
            GLIHUB_ROOT.parent / "yolov5target-main",
        ]
    )
    for c in candidates:
        if c.exists():
            return str(c.resolve())
    return str((GLIHUB_ROOT.parent / "yolov5target-main").resolve())


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_service_host: str = "0.0.0.0"
    ai_service_port: int = 8090

    # GliHub 3.0 Low-Precision & Profile controls
    deploy_profile: str = "cpu-int8"  # cpu-int8 | local-q4 | gpu-pro
    default_precision: str = "int8"   # int8 | fp16 | fp32 | auto
    default_device: str = "auto"
    default_imgsz: int = 640
    cpu_threads: int = 0
    disable_all_plugins: bool = False

    data_dir: str = str((GLIHUB_ROOT / "data").resolve())
    models_dir: str = str((GLIHUB_ROOT / "data" / "models").resolve())
    yolov5_repo_dir: str = _discover_yolov5_dir()
    output_dir: str = str((BASE_DIR / "outputs").resolve())
    yolov5_coupled_person_check: bool = True

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "glihub"
    db_user: str = "postgres"
    db_password: str = "postgres"

    vlm_base_url: str = "http://localhost:11434/v1"
    vlm_api_key: str = ""
    vlm_model: str = "qwen3-vl:4b"
    vlm_timeout_sec: float = 25.0

    llm_base_url: str = "http://localhost:11434/v1"
    llm_api_key: str = ""
    llm_model: str = "qwen3:8b"
    llm_timeout_sec: float = 40.0

    embedding_base_url: str = ""
    embedding_api_key: str = ""
    embedding_model: str = "Qwen/Qwen3-Embedding-0.6B"
    embedding_dim: int = 1024

    ocr_api_base_url: str = ""
    ocr_api_key: str = ""
    ocr_model: str = "deepseek-ocr-2"

    @property
    def pg_dsn(self) -> str:
        return (
            f"host={self.db_host} port={self.db_port} dbname={self.db_name} "
            f"user={self.db_user} password={self.db_password}"
        )

    def resolve_path(self, p: Optional[str]) -> Optional[Path]:
        if not p:
            return None
        path = Path(p)
        if path.is_absolute() and path.exists():
            return path
        # Search across ai-service/, GliHub root, data/, and sibling yolov5target-main!
        search_bases = [BASE_DIR, GLIHUB_ROOT, Path(self.data_dir), GLIHUB_ROOT.parent]
        for base in search_bases:
            cand = (base / p).resolve()
            if cand.exists():
                return cand
        # If caller passed `yolov5target-main/foo/bar.jpg` while repo lives at discovered `yolov5_repo_dir`
        norm_str = str(p).replace("\\", "/")
        if "yolov5target-main/" in norm_str:
            sub_rel = norm_str.split("yolov5target-main/", 1)[1]
            cand_v5 = (Path(self.yolov5_repo_dir) / sub_rel).resolve()
            if cand_v5.exists():
                return cand_v5
        return (GLIHUB_ROOT / path).resolve()


settings = Settings()
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
Path(settings.models_dir).mkdir(parents=True, exist_ok=True)
