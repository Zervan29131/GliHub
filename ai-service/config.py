from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    ai_service_host: str = "0.0.0.0"
    ai_service_port: int = 8090
    default_device: str = "auto"

    yolov5_repo_dir: str = str((BASE_DIR.parent / "yolov5target-main").resolve())
    output_dir: str = str((BASE_DIR / "outputs").resolve())
    yolov5_coupled_person_check: bool = True

    enable_yolo26: bool = True
    enable_rfdetr: bool = False
    enable_yoloe: bool = True

    db_host: str = "localhost"
    db_port: int = 5432
    db_name: str = "glihub"
    db_user: str = "postgres"
    db_password: str = "postgres"

    vlm_base_url: str = "http://localhost:11434/v1"
    vlm_api_key: str = ""
    vlm_model: str = "qwen2.5vl:7b"
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
        if path.is_absolute():
            return path
        candidate_from_service = (BASE_DIR / path).resolve()
        if candidate_from_service.exists():
            return candidate_from_service
        return (BASE_DIR.parent / path).resolve()


settings = Settings()
Path(settings.output_dir).mkdir(parents=True, exist_ok=True)
