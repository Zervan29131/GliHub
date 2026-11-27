#!/usr/bin/env python3
"""GliHub 3.0 Standalone Edge-YOLO26 Service Entrypoint."""
from __future__ import annotations

import argparse
from pathlib import Path
import uvicorn

from core.config_loader import ConfigManager
from web.app import create_edge_app


def cli_entry() -> None:
    parser = argparse.ArgumentParser(description="GliHub 3.0 Standalone YOLO26 Edge Node")
    parser.add_argument("--config", type=str, default="", help="Path to config.yaml")
    parser.add_argument("--host", type=str, default="", help="Override bind host")
    parser.add_argument("--port", type=int, default=0, help="Override bind port (default 8091)")
    args = parser.parse_args()

    cfg_path = Path(args.config).resolve() if args.config else None
    cfg_mgr = ConfigManager(cfg_path)
    host = args.host or cfg_mgr.config.local_host
    port = args.port or cfg_mgr.config.local_port

    app = create_edge_app(config_path=cfg_path, start_loops=True)
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    cli_entry()
