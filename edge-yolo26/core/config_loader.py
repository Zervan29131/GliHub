from __future__ import annotations

import os
import threading
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import yaml


@dataclass
class DynamicFpsConfig:
    enabled: bool = True
    idle_fps: float = 0.5
    active_fps: float = 8.0
    motion_pixel_threshold: float = 0.015


@dataclass
class ChannelConfig:
    channel_code: str = "cam-default-01"
    channel_name: str = "默认边缘监控通道"
    dept_id: int = 103
    place_type: str = "PRODUCTION"
    hazard_id: Optional[int] = None
    stream_source: str = ""
    task_type: str = "detect"  # detect | pose | seg | obb
    conf_threshold: float = 0.35
    silence_window_sec: int = 30
    dynamic_fps: DynamicFpsConfig = field(default_factory=DynamicFpsConfig)
    roi_polygon: List[List[float]] = field(
        default_factory=lambda: [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]]
    )


@dataclass
class EdgeConfig:
    node_code: str = "edge-chem-zone-01"
    node_name: str = "边缘视觉推理节点 #01"
    local_host: str = "0.0.0.0"
    local_port: int = 8091

    center_enabled: bool = True
    center_base_url: str = "http://127.0.0.1:8081"
    edge_token: str = "glihub-edge-shared-token-v3"
    heartbeat_interval_sec: int = 15
    batch_upload_size: int = 10
    flush_interval_sec: float = 3.0
    request_timeout_sec: float = 8.0

    precision_mode: str = "int8"
    primary_model_path: str = "../data/models/yolo26n.int8.onnx"
    ppe_helmet_model_path: str = "../data/models/yolov5_helmet.int8.onnx"
    imgsz: int = 640
    conf_threshold: float = 0.35
    iou_threshold: float = 0.45
    cpu_threads: int = 0

    sqlite_path: str = "./edge_data/offline_outbox.db"
    max_queue_records: int = 5000
    models_dir: str = "../data/models"
    snapshots_dir: str = "./edge_data/snapshots"

    config_version: int = 1
    channels: List[ChannelConfig] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class ConfigManager:
    """Thread-safe configuration manager supporting local YAML + Center hot updates."""

    def __init__(self, config_path: Optional[Path] = None) -> None:
        self._lock = threading.RLock()
        self.base_dir = Path(__file__).resolve().parent.parent
        if config_path is None:
            default_cfg = self.base_dir / "config.yaml"
            example_cfg = self.base_dir / "config.example.yaml"
            self.config_path = default_cfg if default_cfg.exists() else example_cfg
        else:
            self.config_path = Path(config_path).resolve()
        self.config = self._load_from_disk()

    def resolve_path(self, raw_path: str) -> Path:
        p = Path(raw_path)
        if p.is_absolute():
            return p
        return (self.base_dir / p).resolve()

    def _load_from_disk(self) -> EdgeConfig:
        raw: Dict[str, Any] = {}
        if self.config_path.exists():
            with self.config_path.open("r", encoding="utf-8") as f:
                raw = yaml.safe_load(f) or {}

        node = raw.get("node", {})
        center = raw.get("center", {})
        inf = raw.get("inference", {})
        storage = raw.get("storage", {})

        channels: List[ChannelConfig] = []
        for ch in raw.get("channels", []):
            df_raw = ch.get("dynamic_fps", {})
            df = DynamicFpsConfig(
                enabled=bool(df_raw.get("enabled", True)),
                idle_fps=float(df_raw.get("idle_fps", 0.5)),
                active_fps=float(df_raw.get("active_fps", 8.0)),
                motion_pixel_threshold=float(df_raw.get("motion_pixel_threshold", 0.015)),
            )
            channels.append(
                ChannelConfig(
                    channel_code=str(ch.get("channel_code", "cam-01")),
                    channel_name=str(ch.get("channel_name", "边缘通道")),
                    dept_id=int(ch.get("dept_id", 103)),
                    place_type=str(ch.get("place_type", "PRODUCTION")),
                    hazard_id=ch.get("hazard_id"),
                    stream_source=str(ch.get("stream_source", "")),
                    task_type=str(ch.get("task_type", "detect")),
                    conf_threshold=float(ch.get("conf_threshold", inf.get("conf_threshold", 0.35))),
                    silence_window_sec=int(ch.get("silence_window_sec", 30)),
                    dynamic_fps=df,
                    roi_polygon=ch.get("roi_polygon")
                    or [[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0]],
                )
            )

        if not channels:
            channels.append(ChannelConfig())

        return EdgeConfig(
            node_code=os.getenv("EDGE_NODE_CODE", node.get("node_code", "edge-chem-zone-01")),
            node_name=os.getenv("EDGE_NODE_NAME", node.get("node_name", "边缘视觉推理节点 #01")),
            local_host=os.getenv("EDGE_HOST", node.get("local_host", "0.0.0.0")),
            local_port=int(os.getenv("EDGE_PORT", node.get("local_port", 8091))),
            center_enabled=os.getenv("EDGE_CENTER_ENABLED", str(center.get("enabled", True))).lower()
            not in ("0", "false", "no"),
            center_base_url=os.getenv("EDGE_CENTER_URL", center.get("base_url", "http://127.0.0.1:8081")),
            edge_token=os.getenv("EDGE_TOKEN", center.get("edge_token", "glihub-edge-shared-token-v3")),
            heartbeat_interval_sec=int(center.get("heartbeat_interval_sec", 15)),
            batch_upload_size=int(center.get("batch_upload_size", 10)),
            flush_interval_sec=float(center.get("flush_interval_sec", 3.0)),
            request_timeout_sec=float(center.get("request_timeout_sec", 8.0)),
            precision_mode=os.getenv("EDGE_PRECISION", inf.get("precision_mode", "int8")),
            primary_model_path=os.getenv(
                "EDGE_PRIMARY_MODEL", inf.get("primary_model_path", "../data/models/yolo26n.int8.onnx")
            ),
            ppe_helmet_model_path=os.getenv(
                "EDGE_HELMET_MODEL",
                inf.get("ppe_helmet_model_path", "../data/models/yolov5_helmet.int8.onnx"),
            ),
            imgsz=int(os.getenv("EDGE_IMGSZ", inf.get("imgsz", 640))),
            conf_threshold=float(inf.get("conf_threshold", 0.35)),
            iou_threshold=float(inf.get("iou_threshold", 0.45)),
            cpu_threads=int(os.getenv("EDGE_CPU_THREADS", inf.get("cpu_threads", 0))),
            sqlite_path=storage.get("sqlite_path", "./edge_data/offline_outbox.db"),
            max_queue_records=int(storage.get("max_queue_records", 5000)),
            models_dir=storage.get("models_dir", "../data/models"),
            snapshots_dir=storage.get("snapshots_dir", "./edge_data/snapshots"),
            config_version=int(raw.get("config_version", 1)),
            channels=channels,
        )

    def update_channel_roi(
        self,
        channel_code: str,
        roi_polygon: List[List[float]],
        task_type: Optional[str] = None,
        conf_threshold: Optional[float] = None,
    ) -> ChannelConfig:
        with self._lock:
            for ch in self.config.channels:
                if ch.channel_code == channel_code:
                    ch.roi_polygon = roi_polygon
                    if task_type:
                        ch.task_type = task_type
                    if conf_threshold is not None:
                        ch.conf_threshold = float(conf_threshold)
                    self.config.config_version += 1
                    return ch
            new_ch = ChannelConfig(
                channel_code=channel_code,
                roi_polygon=roi_polygon,
                task_type=task_type or "detect",
                conf_threshold=conf_threshold if conf_threshold is not None else self.config.conf_threshold,
            )
            self.config.channels.append(new_ch)
            self.config.config_version += 1
            return new_ch

    def apply_remote_config(self, payload: Dict[str, Any]) -> bool:
        with self._lock:
            remote_ver = int(payload.get("configVersion", 0))
            if remote_ver <= self.config.config_version:
                return False
            if "confThres" in payload and payload["confThres"] is not None:
                self.config.conf_threshold = float(payload["confThres"])
            remote_channels = payload.get("channels") or []
            by_code = {c.channel_code: c for c in self.config.channels}
            for rc in remote_channels:
                code = rc.get("channelCode")
                if not code:
                    continue
                target = by_code.get(code)
                if target is None:
                    target = ChannelConfig(channel_code=code, channel_name=rc.get("channelName", code))
                    self.config.channels.append(target)
                if rc.get("taskType"):
                    target.task_type = str(rc["taskType"])
                if rc.get("roiPolygon"):
                    target.roi_polygon = rc["roiPolygon"]
                if rc.get("confThreshold") is not None:
                    target.conf_threshold = float(rc["confThreshold"])
                if rc.get("silenceWindowSec") is not None:
                    target.silence_window_sec = int(rc["silenceWindowSec"])
                if rc.get("deptId") is not None:
                    target.dept_id = int(rc["deptId"])
                if rc.get("placeType"):
                    target.place_type = str(rc["placeType"])
            self.config.config_version = remote_ver
            return True
