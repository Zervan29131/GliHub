from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple
import httpx

from core.config_loader import ConfigManager


class CloudSyncClient:
    """
    Lightweight HTTP/JSON Edge-to-Center client using `X-Edge-Token`.
    Designed so Center downtime never crashes or blocks local edge inference.
    """

    def __init__(self, cfg_mgr: ConfigManager) -> None:
        self.cfg_mgr = cfg_mgr
        self.center_online: bool = False
        self.last_sync_error: Optional[str] = None
        self.registered_node_id: Optional[int] = None

    def _headers(self) -> Dict[str, str]:
        return {
            "X-Edge-Token": self.cfg_mgr.config.edge_token,
            "Content-Type": "application/json",
        }

    async def register(self, runtime_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cfg = self.cfg_mgr.config
        if not cfg.center_enabled:
            return None
        url = f"{cfg.center_base_url.rstrip('/')}/ehs/edge/register"
        payload = {
            "nodeCode": cfg.node_code,
            "nodeName": cfg.node_name,
            "osArch": runtime_info.get("os_arch", ""),
            "chipModel": runtime_info.get("chip_model", ""),
            "precisionMode": runtime_info.get("precision_mode", cfg.precision_mode),
            "activeModelCode": runtime_info.get("model_file", ""),
            "activeModelSha256": runtime_info.get("model_sha256", ""),
            "localDebugUrl": f"http://127.0.0.1:{cfg.local_port}",
            "configVersion": cfg.config_version,
            "channels": [
                {
                    "channelCode": c.channel_code,
                    "channelName": c.channel_name,
                    "deptId": c.dept_id,
                    "placeType": c.place_type,
                    "hazardId": c.hazard_id,
                    "streamSource": c.stream_source,
                    "taskType": c.task_type,
                    "roiPolygon": c.roi_polygon,
                    "confThreshold": c.conf_threshold,
                }
                for c in cfg.channels
            ],
        }
        try:
            async with httpx.AsyncClient(timeout=cfg.request_timeout_sec) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                body = resp.json()
                data = body.get("data", body) if isinstance(body, dict) else {}
                self.center_online = True
                self.last_sync_error = None
                if isinstance(data, dict) and data.get("nodeId"):
                    self.registered_node_id = int(data["nodeId"])
                return data if isinstance(data, dict) else {}
        except Exception as exc:
            self.center_online = False
            self.last_sync_error = str(exc)
            return None

    async def heartbeat(self, metrics: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        cfg = self.cfg_mgr.config
        if not cfg.center_enabled:
            return None
        url = f"{cfg.center_base_url.rstrip('/')}/ehs/edge/heartbeat"
        try:
            async with httpx.AsyncClient(timeout=cfg.request_timeout_sec) as client:
                resp = await client.post(url, json=metrics, headers=self._headers())
                resp.raise_for_status()
                body = resp.json()
                self.center_online = True
                self.last_sync_error = None
                return body.get("data", body) if isinstance(body, dict) else {}
        except Exception as exc:
            self.center_online = False
            self.last_sync_error = str(exc)
            return None

    async def upload_alerts_batch(self, events: List[Dict[str, Any]]) -> Tuple[bool, List[str], str]:
        cfg = self.cfg_mgr.config
        if not cfg.center_enabled or not events:
            return False, [], "Center sync disabled or empty batch"
        url = f"{cfg.center_base_url.rstrip('/')}/ehs/edge/alerts/batch"
        payload = {
            "nodeCode": cfg.node_code,
            "nodeName": cfg.node_name,
            "events": events,
        }
        try:
            async with httpx.AsyncClient(timeout=cfg.request_timeout_sec) as client:
                resp = await client.post(url, json=payload, headers=self._headers())
                resp.raise_for_status()
                body = resp.json()
                data = body.get("data", body) if isinstance(body, dict) else {}
                accepted = data.get("acceptedUuids") if isinstance(data, dict) else None
                if not accepted:
                    accepted = [ev["alertUuid"] for ev in events]
                self.center_online = True
                self.last_sync_error = None
                return True, list(accepted), ""
        except Exception as exc:
            self.center_online = False
            self.last_sync_error = str(exc)
            return False, [], str(exc)

    async def fetch_remote_config(self) -> Optional[Dict[str, Any]]:
        cfg = self.cfg_mgr.config
        if not cfg.center_enabled:
            return None
        url = f"{cfg.center_base_url.rstrip('/')}/ehs/edge/config/{cfg.node_code}"
        try:
            async with httpx.AsyncClient(timeout=cfg.request_timeout_sec) as client:
                resp = await client.get(url, headers=self._headers())
                resp.raise_for_status()
                body = resp.json()
                return body.get("data", body) if isinstance(body, dict) else None
        except Exception:
            return None
