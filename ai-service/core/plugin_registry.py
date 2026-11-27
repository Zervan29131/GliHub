from __future__ import annotations

import importlib
import json
import threading
from pathlib import Path
from typing import Any, Dict, List, Optional

from config import BASE_DIR, settings
from core.precision import precision_manager


class BaseAiPlugin:
    """Base lifecycle contract for all 7 GliHub 3.0 optional AI plugins."""

    def __init__(self, manifest: Dict[str, Any]) -> None:
        self.manifest = manifest
        self.plugin_id: str = manifest["plugin_id"]

    def check_readiness(self) -> Tuple_Status:
        """Returns (ready_bool, detail_msg). Subclasses may override."""
        return True, "Ready"

    def runtime_metadata(self) -> Dict[str, Any]:
        return {}


Tuple_Status = tuple[bool, str]


class PluginRegistry:
    """
    Discovers `plugins/mod_*/manifest.json`, manages hot-plugging & install state,
    and guarantees 0-plugin zero-crash execution.
    """

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self.plugins_root = BASE_DIR / "plugins"
        self.state_path = Path(settings.data_dir) / "ai_plugins_state.json"
        self._manifests: Dict[str, Dict[str, Any]] = {}
        self._instances: Dict[str, BaseAiPlugin] = {}
        self._state_overrides: Dict[str, Dict[str, Any]] = self._load_state_file()
        self.reload_manifests()

    def _load_state_file(self) -> Dict[str, Dict[str, Any]]:
        if self.state_path.exists():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_state_file(self) -> None:
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(
            json.dumps(self._state_overrides, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

    def reload_manifests(self) -> None:
        with self._lock:
            self._manifests.clear()
            if not self.plugins_root.exists():
                return
            for mf_path in sorted(self.plugins_root.glob("*/manifest.json")):
                try:
                    mf = json.loads(mf_path.read_text(encoding="utf-8"))
                    pid = mf.get("plugin_id")
                    if pid:
                        mf["_dir"] = str(mf_path.parent)
                        self._manifests[pid] = mf
                except Exception:
                    continue

    def _check_imports(self, required_imports: List[str]) -> tuple[bool, List[str]]:
        missing: List[str] = []
        for mod_name in required_imports:
            try:
                importlib.import_module(mod_name)
            except ImportError:
                missing.append(mod_name)
        return len(missing) == 0, missing

    def is_enabled(self, plugin_id: str) -> bool:
        if settings.disable_all_plugins:
            return False
        mf = self._manifests.get(plugin_id)
        if not mf:
            return False
        ov = self._state_overrides.get(plugin_id, {})
        if "enabled" in ov:
            return bool(ov["enabled"])
        return bool(mf.get("default_enabled", True))

    def get_plugin_status(self, plugin_id: str) -> Dict[str, Any]:
        mf = self._manifests.get(plugin_id)
        if not mf:
            return {"plugin_id": plugin_id, "status": "UNKNOWN", "installed": False, "enabled": False}

        hw = precision_manager.detect_hardware()
        imports_ok, missing_pkgs = self._check_imports(mf.get("required_imports", []))
        requires_gpu = bool(mf.get("requires_gpu", False))
        gpu_ok = (not requires_gpu) or hw["has_dedicated_gpu"] or (
            precision_manager.deploy_profile == "gpu-pro"
        )

        enabled = self.is_enabled(plugin_id)
        ov = self._state_overrides.get(plugin_id, {})
        pref_prec = ov.get("preferred_precision") or mf.get(
            "default_precision_cpu", precision_manager.preferred_precision
        )

        extra_detail: Dict[str, Any] = {}
        ready_extra = True
        ready_msg = "就绪"
        if imports_ok and gpu_ok:
            inst = self.get_instance(plugin_id)
            if inst is not None:
                ready_extra, ready_msg = inst.check_readiness()
                extra_detail = inst.runtime_metadata()

        if not imports_ok:
            status = "NOT_INSTALLED"
            reason = f"未安装依赖 ({', '.join(missing_pkgs)})，可执行 `uv sync --extra {mf.get('uv_extra', '')}` 选装"
        elif requires_gpu and not gpu_ok:
            status = "GPU_REQUIRED"
            reason = "当前为无独显低功耗环境 (cpu-int8/local-q4)，该高精度 Transformer 插件需 GPU (`gpu-pro` 档) 解锁"
        elif not enabled:
            status = "DISABLED"
            reason = "已在模型选装中心手动停用（零内存驻留）"
        elif not ready_extra:
            status = "DEGRADED_FALLBACK"
            reason = ready_msg
        else:
            status = "ACTIVE"
            reason = ready_msg

        uv_extra = mf.get("uv_extra", "")
        return {
            "plugin_id": plugin_id,
            "name": mf.get("name", plugin_id),
            "layer": mf.get("layer", ""),
            "order": mf.get("order", 99),
            "description": mf.get("description", ""),
            "uv_extra": uv_extra,
            "install_command": f"uv sync --extra {uv_extra}" if uv_extra else "内置免装",
            "requires_gpu": requires_gpu,
            "min_ram_mb": mf.get("min_ram_mb", 128),
            "supported_precisions": mf.get("supported_precisions", ["int8"]),
            "preferred_precision": pref_prec,
            "installed": imports_ok,
            "missing_packages": missing_pkgs,
            "enabled": enabled,
            "active": status in ("ACTIVE", "DEGRADED_FALLBACK") and enabled and imports_ok,
            "status": status,
            "status_reason": reason,
            "fallback_behavior": mf.get("fallback_behavior", ""),
            "provider_endpoint": ov.get("provider_endpoint", ""),
            "provider_model": ov.get("provider_model", ""),
            "runtime": extra_detail,
        }

    def list_plugins(self) -> List[Dict[str, Any]]:
        items = [self.get_plugin_status(pid) for pid in self._manifests]
        items.sort(key=lambda x: int(x.get("order", 99)))
        return items

    def get_instance(self, plugin_id: str) -> Optional[BaseAiPlugin]:
        with self._lock:
            if plugin_id in self._instances:
                return self._instances[plugin_id]
            mf = self._manifests.get(plugin_id)
            if not mf:
                return None
            imports_ok, _ = self._check_imports(mf.get("required_imports", []))
            if not imports_ok:
                return None
            ep = mf.get("entrypoint", "")
            if ":" not in ep:
                return None
            mod_path, cls_name = ep.split(":", 1)
            try:
                mod = importlib.import_module(mod_path)
                cls = getattr(mod, cls_name)
                inst = cls(mf)
                self._instances[plugin_id] = inst
                return inst
            except Exception:
                return None

    def get_active_instance(self, plugin_id: str) -> Optional[BaseAiPlugin]:
        st = self.get_plugin_status(plugin_id)
        if not st.get("installed") or not st.get("enabled"):
            return None
        if st.get("status") == "GPU_REQUIRED":
            return None
        return self.get_instance(plugin_id)

    def configure_plugin(
        self,
        plugin_id: str,
        *,
        enabled: Optional[bool] = None,
        preferred_precision: Optional[str] = None,
        provider_endpoint: Optional[str] = None,
        provider_model: Optional[str] = None,
    ) -> Dict[str, Any]:
        if plugin_id not in self._manifests:
            raise KeyError(f"Unknown plugin_id: {plugin_id}")
        with self._lock:
            cur = dict(self._state_overrides.get(plugin_id, {}))
            if enabled is not None:
                cur["enabled"] = bool(enabled)
            if preferred_precision:
                cur["preferred_precision"] = preferred_precision
            if provider_endpoint is not None:
                cur["provider_endpoint"] = provider_endpoint
            if provider_model is not None:
                cur["provider_model"] = provider_model
            self._state_overrides[plugin_id] = cur
            # Drop cached instance if disabled or precision changed so memory is freed / reloaded
            if enabled is False or preferred_precision:
                self._instances.pop(plugin_id, None)
            self._save_state_file()
        return self.get_plugin_status(plugin_id)


plugin_registry = PluginRegistry()
