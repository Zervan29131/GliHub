from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional
import httpx

from core.precision_runtime import OnnxYoloEngine


class OtaModelUpdater:
    """
    Atomic SHA256-verified OTA model updater for edge nodes.
    Downloads `.int8.onnx` / `.fp16.onnx` to a temporary file, verifies SHA256 digest,
    atomically replaces target file, and hot-reloads OnnxYoloEngine without dropping frames.
    """

    def __init__(self, models_dir: Path, engine: OnnxYoloEngine, edge_token: str = "") -> None:
        self.models_dir = Path(models_dir).resolve()
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.engine = engine
        self.edge_token = edge_token

    async def apply_ota(
        self,
        download_url: str,
        target_filename: str,
        expected_sha256: Optional[str] = None,
    ) -> Dict[str, Any]:
        safe_name = Path(target_filename).name
        if not safe_name.endswith(".onnx"):
            raise ValueError("OTA model filename must end with .onnx")

        final_path = self.models_dir / safe_name
        temp_path = self.models_dir / f".{safe_name}.ota.part"

        hasher = hashlib.sha256()
        headers = {"X-Edge-Token": self.edge_token} if self.edge_token else {}

        if download_url.startswith(("http://", "https://")):
            async with httpx.AsyncClient(timeout=60.0, follow_redirects=True) as client:
                async with client.stream("GET", download_url, headers=headers) as resp:
                    resp.raise_for_status()
                    with temp_path.open("wb") as f:
                        async for chunk in resp.aiter_bytes(chunk_size=256 * 1024):
                            f.write(chunk)
                            hasher.update(chunk)
        else:
            # Support local file path for offline USB/LAN staging & unit testing
            src = Path(download_url).resolve()
            if not src.exists():
                raise FileNotFoundError(f"Local OTA source not found: {src}")
            with src.open("rb") as rf, temp_path.open("wb") as wf:
                for chunk in iter(lambda: rf.read(256 * 1024), b""):
                    wf.write(chunk)
                    hasher.update(chunk)

        actual_sha = hasher.hexdigest()
        if expected_sha256 and actual_sha.lower() != expected_sha256.strip().lower():
            temp_path.unlink(missing_ok=True)
            raise ValueError(
                f"OTA SHA256 mismatch! expected={expected_sha256}, actual={actual_sha}"
            )

        os.replace(temp_path, final_path)
        info = self.engine.reload_model(final_path)
        return {
            "status": "APPLIED",
            "model_file": safe_name,
            "sha256": actual_sha,
            "runtime": info,
        }
