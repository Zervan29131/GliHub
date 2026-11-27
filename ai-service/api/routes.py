import base64
from pathlib import Path
from typing import Any, Dict, List, Optional
import uuid

from fastapi import APIRouter, File, Form, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from adapters.registry import registry
from agents.emergency_agent import generate_emergency_action_card
from agents.eval_agent import generate_eval_report, recommend_eval_params
from config import settings
from rag.retriever import rag_engine
from vlm.reviewer import vlm_reviewer

router = APIRouter(prefix="/api/v1")


class RegisterModelRequest(BaseModel):
    model_code: str
    weights_path: str


class VisionAnalyzeRequest(BaseModel):
    image_path: Optional[str] = None
    image_base64: Optional[str] = None
    model_code: str = "yolov5_helmet_local"
    prompt_text: Optional[str] = None
    conf_thres: float = 0.35
    iou_thres: float = 0.45
    enable_vlm: bool = True
    place_type: str = "production"
    area_name: str = "采油作业区"
    hazard_context: Optional[str] = None


class VisionRecheckRequest(BaseModel):
    after_image_path: Optional[str] = None
    after_image_base64: Optional[str] = None
    hazard_title: str
    model_code: str = "yolov5_helmet_local"
    prompt_text: Optional[str] = None


class RagIngestRequest(BaseModel):
    doc_title: str
    doc_category: str = "STANDARD"
    standard_code: Optional[str] = None
    file_path: Optional[str] = None
    raw_text: Optional[str] = None
    applicable_places: str = "production,storage,auxiliary"
    notice_id: Optional[int] = None


class RagSearchRequest(BaseModel):
    query: str
    place_type: Optional[str] = None
    top_k: int = 4


class RagChatRequest(BaseModel):
    messages: List[Dict[str, str]] = Field(default_factory=list)
    place_type: Optional[str] = None
    context_summary: Optional[str] = None


class EvalAssistRequest(BaseModel):
    eval_method: str = "LEC"
    place_type: str = "production"
    area_name: str = "采油作业区"
    hazard_profile: Optional[Dict[str, Any]] = None
    recent_alerts_count: int = 0
    open_orders_count: int = 0


class EvalReportRequest(BaseModel):
    place_type: str = "production"
    area_name: str = "采油作业区"
    eval_summary: Dict[str, Any] = Field(default_factory=dict)
    hazard_profiles: Optional[List[Dict[str, Any]]] = None
    alert_stats: Optional[Dict[str, Any]] = None
    order_stats: Optional[Dict[str, Any]] = None


class EmergencyCardRequest(BaseModel):
    hazard_profile: Dict[str, Any] = Field(default_factory=dict)
    accident_type: str = "可燃气体泄漏蒸气云爆炸"
    leak_mass_kg: float = 2000.0
    wind_direction: str = "东南风"
    wind_speed_ms: float = 3.2
    tnt_result: Dict[str, Any] = Field(default_factory=dict)
    affected_equips: List[Dict[str, Any]] = Field(default_factory=list)
    affected_staff_count: int = 6


def _materialize_image(image_path: Optional[str], image_base64: Optional[str]) -> Path:
    if image_path:
        resolved = settings.resolve_path(image_path)
        if resolved and resolved.exists():
            return resolved
        raise HTTPException(status_code=400, detail=f"指定的图像路径不存在: {image_path}")
    if image_base64:
        b64_clean = image_base64.split(",", 1)[-1]
        raw = base64.b64decode(b64_clean)
        tmp_dir = Path(settings.output_dir) / "uploads"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        out = tmp_dir / f"upload_{uuid.uuid4().hex[:10]}.jpg"
        out.write_bytes(raw)
        return out
    raise HTTPException(status_code=400, detail="必须提供 image_path 或 image_base64")


@router.get("/health")
async def health_check():
    vlm_live = await vlm_reviewer.is_endpoint_reachable()
    return {
        "status": "ok",
        "service": "glihub-ai-service",
        "version": "2.0.0",
        "optimal_device": registry.device,
        "yolov5_repo_exists": Path(settings.yolov5_repo_dir).exists(),
        "pgvector_enabled": rag_engine.has_pgvector(),
        "vlm_live_endpoint": vlm_live,
        "vlm_model": settings.vlm_model,
        "llm_model": settings.llm_model,
        "models": registry.list_models(),
    }


@router.get("/vision/models")
async def list_vision_models():
    return {"models": registry.list_models()}


@router.post("/vision/register")
async def register_custom_model(req: RegisterModelRequest):
    registry.register_custom_yolov5(req.model_code, req.weights_path)
    return {"status": "registered", "models": registry.list_models()}


async def _run_full_vision_pipeline(
    img_file: Path,
    model_code: str,
    prompt_text: Optional[str],
    conf_thres: float,
    iou_thres: float,
    enable_vlm: bool,
    place_type: str,
    area_name: str,
    hazard_context: Optional[str],
) -> Dict[str, Any]:
    stage1 = registry.predict(
        image_path=img_file,
        model_code=model_code,
        conf_thres=conf_thres,
        iou_thres=iou_thres,
        prompt_text=prompt_text,
    )

    vlm_res = None
    cited_laws: List[Dict[str, Any]] = []
    if enable_vlm:
        vlm_res = await vlm_reviewer.review(
            image_path=img_file,
            detections=stage1.detections,
            place_type=place_type,
            area_name=area_name,
            hazard_context=hazard_context,
            prompt_text=prompt_text,
        )
        if vlm_res.is_real_hazard:
            cited_laws = await rag_engine.search(
                f"{vlm_res.violation_type} {prompt_text or ''}",
                place_type=place_type,
                top_k=3,
            )

    return {
        "vision": stage1.model_dump(),
        "vlm_review": vlm_res.model_dump() if vlm_res else None,
        "cited_laws": cited_laws,
    }


@router.post("/vision/analyze")
async def analyze_vision(req: VisionAnalyzeRequest):
    img_file = _materialize_image(req.image_path, req.image_base64)
    return await _run_full_vision_pipeline(
        img_file=img_file,
        model_code=req.model_code,
        prompt_text=req.prompt_text,
        conf_thres=req.conf_thres,
        iou_thres=req.iou_thres,
        enable_vlm=req.enable_vlm,
        place_type=req.place_type,
        area_name=req.area_name,
        hazard_context=req.hazard_context,
    )


@router.post("/vision/analyze-upload")
async def analyze_vision_upload(
    file: UploadFile = File(...),
    model_code: str = Form("yolov5_helmet_local"),
    prompt_text: Optional[str] = Form(None),
    conf_thres: float = Form(0.35),
    iou_thres: float = Form(0.45),
    enable_vlm: bool = Form(True),
    place_type: str = Form("production"),
    area_name: str = Form("采油作业区"),
    hazard_context: Optional[str] = Form(None),
):
    tmp_dir = Path(settings.output_dir) / "uploads"
    tmp_dir.mkdir(parents=True, exist_ok=True)
    suffix = Path(file.filename or "frame.jpg").suffix or ".jpg"
    save_file = tmp_dir / f"up_{uuid.uuid4().hex[:10]}{suffix}"
    save_file.write_bytes(await file.read())

    res = await _run_full_vision_pipeline(
        img_file=save_file,
        model_code=model_code,
        prompt_text=prompt_text,
        conf_thres=conf_thres,
        iou_thres=iou_thres,
        enable_vlm=enable_vlm,
        place_type=place_type,
        area_name=area_name,
        hazard_context=hazard_context,
    )
    res["raw_image_url"] = f"/outputs/uploads/{save_file.name}"
    return res


@router.post("/vision/recheck")
async def recheck_rectification(req: VisionRecheckRequest):
    img_file = _materialize_image(req.after_image_path, req.after_image_base64)
    stage1 = registry.predict(
        image_path=img_file,
        model_code=req.model_code,
        conf_thres=0.35,
        iou_thres=0.45,
        prompt_text=req.prompt_text,
    )
    violations = [d.model_dump() for d in stage1.detections if d.is_violation]
    passed = len(violations) == 0
    comment = (
        f"AI 复检通过：复查画面未再检出「{req.hazard_title}」相关违章特征（合规目标数：{len(stage1.detections)}），准予销项闭环。"
        if passed
        else f"AI 复检未通过：画面中仍检出 {len(violations)} 处违章目标，请继续整改后重新上传复查图。"
    )
    return {
        "passed": passed,
        "annotated_image_url": stage1.annotated_image_url,
        "remaining_violations": violations,
        "review_comment": comment,
    }


@router.post("/rag/ingest")
async def rag_ingest(req: RagIngestRequest):
    return await rag_engine.ingest_document(
        doc_title=req.doc_title,
        doc_category=req.doc_category,
        standard_code=req.standard_code,
        file_path=req.file_path,
        raw_text=req.raw_text,
        applicable_places=req.applicable_places,
        notice_id=req.notice_id,
    )


@router.post("/rag/search")
async def rag_search(req: RagSearchRequest):
    items = await rag_engine.search(req.query, place_type=req.place_type, top_k=req.top_k)
    return {"items": items}


@router.post("/rag/chat/stream")
async def rag_chat_stream(req: RagChatRequest):
    return StreamingResponse(
        rag_engine.stream_chat(
            messages=req.messages,
            place_type=req.place_type,
            context_summary=req.context_summary,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/agents/eval-assist")
async def eval_assist(req: EvalAssistRequest):
    return await recommend_eval_params(
        eval_method=req.eval_method,
        place_type=req.place_type,
        area_name=req.area_name,
        hazard_profile=req.hazard_profile,
        recent_alerts_count=req.recent_alerts_count,
        open_orders_count=req.open_orders_count,
    )


@router.post("/agents/eval-report")
async def eval_report(req: EvalReportRequest):
    return await generate_eval_report(
        place_type=req.place_type,
        area_name=req.area_name,
        eval_summary=req.eval_summary,
        hazard_profiles=req.hazard_profiles,
        alert_stats=req.alert_stats,
        order_stats=req.order_stats,
    )


@router.post("/agents/emergency-card")
async def emergency_card(req: EmergencyCardRequest):
    return await generate_emergency_action_card(
        hazard_profile=req.hazard_profile,
        accident_type=req.accident_type,
        leak_mass_kg=req.leak_mass_kg,
        wind_direction=req.wind_direction,
        wind_speed_ms=req.wind_speed_ms,
        tnt_result=req.tnt_result,
        affected_equips=req.affected_equips,
        affected_staff_count=req.affected_staff_count,
    )
