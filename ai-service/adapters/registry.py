from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional
from PIL import Image

from adapters.base import VisionInferenceOutput, render_detections
from config import settings
from core.plugin_registry import plugin_registry
from core.precision import precision_manager


MODEL_TO_PLUGIN = {
    "yolov5_helmet_local": "mod-yolov5",
    "yolov5s_coco_local": "mod-yolov5",
    "yolo26n_rt": "mod-yolo26",
    "rfdetr_precision": "mod-rfdetr",
    "yoloe_zero_shot": "mod-yoloe",
}


class PluginBackedVisionRouter:
    """
    Routes vision inference requests across the 4 modular vision plugins (`mod-yolov5`, `mod-yolo26`, `mod-rfdetr`, `mod-yoloe`).
    Guarantees 0-crash graceful fallback even when 0 plugins are installed or enabled.
    """

    def __init__(self) -> None:
        self._custom_codes: Dict[str, str] = {}

    @property
    def device(self) -> str:
        hw = precision_manager.detect_hardware()
        return f"{hw['accelerator_tier']}:{precision_manager.preferred_precision}"

    def list_models(self) -> List[Dict[str, Any]]:
        p_status = {p["plugin_id"]: p for p in plugin_registry.list_plugins()}
        catalog = [
            {
                "model_code": "yolov5_helmet_local",
                "name": "自训安全帽检测模型 (YOLOv5 ONNX INT8)",
                "plugin_id": "mod-yolov5",
                "task": "安全帽佩戴耦合研判",
                "precision": p_status.get("mod-yolov5", {}).get("preferred_precision", "int8"),
                "ready": p_status.get("mod-yolov5", {}).get("active", False),
                "status": p_status.get("mod-yolov5", {}).get("status", "NOT_INSTALLED"),
            },
            {
                "model_code": "yolo26n_rt",
                "name": "Ultralytics YOLO26n 无NMS实时模型 (INT8)",
                "plugin_id": "mod-yolo26",
                "task": "无NMS极速检测/姿态/分割/旋转框",
                "precision": p_status.get("mod-yolo26", {}).get("preferred_precision", "int8"),
                "ready": p_status.get("mod-yolo26", {}).get("active", False),
                "status": p_status.get("mod-yolo26", {}).get("status", "NOT_INSTALLED"),
            },
            {
                "model_code": "yoloe_zero_shot",
                "name": "Ultralytics YOLOE 开放词汇零样本检测",
                "plugin_id": "mod-yoloe",
                "task": "输入任意中文排查词即时检出",
                "precision": p_status.get("mod-yoloe", {}).get("preferred_precision", "int8"),
                "ready": p_status.get("mod-yoloe", {}).get("active", False),
                "status": p_status.get("mod-yoloe", {}).get("status", "NOT_INSTALLED"),
            },
            {
                "model_code": "rfdetr_precision",
                "name": "RF-DETR 化工管廊高精度检测 (GPU FP16)",
                "plugin_id": "mod-rfdetr",
                "task": "微小泄漏/仪表异常高精度定位",
                "precision": "fp16",
                "ready": p_status.get("mod-rfdetr", {}).get("active", False),
                "status": p_status.get("mod-rfdetr", {}).get("status", "GPU_REQUIRED"),
            },
            {
                "model_code": "yolov5s_coco_local",
                "name": "通用工业人车物基线模型 (ONNX INT8)",
                "plugin_id": "mod-yolov5",
                "task": "人员/车辆/违规手机通用识别",
                "precision": "int8",
                "ready": p_status.get("mod-yolov5", {}).get("active", False),
                "status": p_status.get("mod-yolov5", {}).get("status", "NOT_INSTALLED"),
            },
        ]
        for code, w_path in self._custom_codes.items():
            catalog.append(
                {
                    "model_code": code,
                    "name": f"自定义注册模型 ({code})",
                    "plugin_id": "mod-yolov5",
                    "task": w_path,
                    "precision": "int8",
                    "ready": p_status.get("mod-yolov5", {}).get("active", False),
                    "status": p_status.get("mod-yolov5", {}).get("status", "NOT_INSTALLED"),
                }
            )
        return catalog

    def register_custom_yolov5(self, model_code: str, weights_path: str) -> None:
        inst = plugin_registry.get_active_instance("mod-yolov5")
        if inst is not None and hasattr(inst, "register_custom_weight"):
            inst.register_custom_weight(model_code, weights_path)  # type: ignore
        self._custom_codes[model_code] = weights_path

    def predict(
        self,
        image_path: Path,
        model_code: str = "yolov5_helmet_local",
        conf_thres: float = 0.35,
        iou_thres: float = 0.45,
        prompt_text: Optional[str] = None,
    ) -> VisionInferenceOutput:
        target_pid = MODEL_TO_PLUGIN.get(model_code, "mod-yolov5")
        if prompt_text and model_code == "yoloe_zero_shot":
            target_pid = "mod-yoloe"

        inst = plugin_registry.get_active_instance(target_pid)
        fallback_note: Optional[str] = None

        # Graceful cross-plugin fallback (e.g., if `mod-rfdetr` requested on CPU -> route to `mod-yolo26` / `mod-yolov5`)
        if inst is None:
            orig_st = plugin_registry.get_plugin_status(target_pid)
            for alt_pid in ("mod-yolo26", "mod-yolov5"):
                alt_inst = plugin_registry.get_active_instance(alt_pid)
                if alt_inst is not None:
                    inst = alt_inst
                    fallback_note = f"{target_pid} 处于 {orig_st['status']} 状态，已自动平滑降级至 {alt_pid} 低精度引擎"
                    target_pid = alt_pid
                    break

        if inst is not None:
            if target_pid == "mod-yoloe":
                out = inst.predict(  # type: ignore
                    image_path=image_path,
                    prompt_text=prompt_text,
                    model_code=model_code,
                    conf_thres=conf_thres,
                    iou_thres=iou_thres,
                )
            elif target_pid == "mod-rfdetr":
                out = inst.predict(image_path=image_path, model_code=model_code, conf_thres=conf_thres)  # type: ignore
            else:
                out = inst.predict(  # type: ignore
                    image_path=image_path,
                    model_code=model_code,
                    conf_thres=conf_thres,
                    iou_thres=iou_thres,
                )
            if fallback_note:
                out.fallback_used = True
                out.note = fallback_note
            return out

        # 0-Plugin Installed/Enabled Graceful No-Op Response (Never 500 crashes!)
        with Image.open(image_path) as im:
            w, h = im.size
        save_p, url = render_detections(image_path, [], Path(settings.output_dir), prefix="noop_0plugin")
        return VisionInferenceOutput(
            model_code=model_code,
            adapter_type="zero-plugin-safe-mode",
            device="cpu-noop",
            inference_ms=1,
            image_width=w,
            image_height=h,
            annotated_image_path=str(save_p),
            annotated_image_url=url,
            detections=[],
            has_violation=False,
            fallback_used=True,
            precision="none",
            plugin_id=None,
            note="当前未选装或已停用全部中心视觉插件 (0-Plugin Mode)；可在「AI 模型选装中心」启用或使用独立边缘节点 edge-yolo26。",
        )


registry = PluginBackedVisionRouter()
