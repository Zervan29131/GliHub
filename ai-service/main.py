from pathlib import Path
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.routes import router as api_v1_router
from config import settings

app = FastAPI(
    title="GliHub 2.0 AI-EHS Engine Service",
    description="多模型工业视觉感知（YOLOv5本地权重 / YOLO26 / RF-DETR / YOLOE）、VLM 二次复核、EHS 法规 RAG 与安全评价/应急推演智能体服务",
    version="2.0.0",
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
        "service": "GliHub 2.0 AI-EHS Engine",
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.ai_service_host,
        port=settings.ai_service_port,
        reload=False,
    )
