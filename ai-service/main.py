from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_v1_router
from config import settings

app = FastAPI(
    title="GliHub 3.0 Modular AI-EHS Engine Service",
    description=(
        "GliHub 3.0 端云协同 7 层可插拔选装 AI 引擎："
        "mod-yolov5 / mod-yolo26 / mod-rfdetr / mod-yoloe / mod-vlm / mod-llm-rag / mod-ocr，"
        "支持无独显 CPU INT8 / Q4_K_M 低精度推理与 0 选装安全降级运行。"
    ),
    version="3.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

out_path = Path(settings.output_dir)
out_path.mkdir(parents=True, exist_ok=True)
app.mount("/outputs", StaticFiles(directory=str(out_path)), name="outputs")
app.include_router(api_v1_router)


@app.get("/")
async def root():
    return {
        "service": "GliHub 3.0 Modular AI-EHS Engine",
        "version": "3.0.0",
        "deploy_profile": settings.deploy_profile,
        "docs": "/docs",
        "health": "/api/v1/health",
        "plugins": "/api/v1/plugins",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.ai_service_host,
        port=settings.ai_service_port,
        reload=False,
    )
