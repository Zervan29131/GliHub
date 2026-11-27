from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict, List, Optional

import cv2
import numpy as np
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from core.config_loader import ConfigManager
from core.pipeline import EdgePipelineService


class RoiUpdateRequest(BaseModel):
    channel_code: str = "cam-tank-01"
    roi_polygon: List[List[float]]
    task_type: Optional[str] = None
    conf_threshold: Optional[float] = None


class OtaRequest(BaseModel):
    download_url: str
    target_filename: str
    expected_sha256: Optional[str] = None


DEBUG_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>GliHub 3.0 Edge-YOLO26 边缘自治推理调试台</title>
<style>
  :root { --bg:#0b1220; --panel:#111b2e; --border:#1f3152; --accent:#00d4ff; --ok:#10b981; --warn:#f59e0b; --err:#ef4444; --txt:#e2e8f0; --muted:#94a3b8; }
  * { box-sizing:border-box; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif; }
  body { margin:0; background:var(--bg); color:var(--txt); padding:18px; }
  header { display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid var(--border); padding-bottom:12px; margin-bottom:16px; }
  .badge { padding:4px 10px; border-radius:999px; font-size:12px; font-weight:600; background:#172554; color:var(--accent); border:1px solid #1d4ed8; }
  .badge.ok { background:#064e3b; color:#34d399; border-color:#059669; }
  .badge.warn { background:#451a03; color:#fbbf24; border-color:#d97706; }
  .grid { display:grid; grid-template-columns: 1.35fr 1fr; gap:16px; }
  .card { background:var(--panel); border:1px solid var(--border); border-radius:10px; padding:16px; }
  h3 { margin:0 0 12px 0; font-size:15px; color:var(--accent); }
  .kpis { display:grid; grid-template-columns:repeat(4,1fr); gap:10px; margin-bottom:16px; }
  .kpi { background:#0f172a; border:1px solid var(--border); border-radius:8px; padding:10px 12px; }
  .kpi .lbl { font-size:12px; color:var(--muted); }
  .kpi .val { font-size:20px; font-weight:700; margin-top:4px; }
  .row { display:flex; gap:8px; flex-wrap:wrap; align-items:center; margin-bottom:10px; }
  select, input[type="text"], button { background:#0f172a; color:var(--txt); border:1px solid var(--border); border-radius:6px; padding:7px 11px; font-size:13px; }
  button { cursor:pointer; background:#1d4ed8; border-color:#2563eb; font-weight:600; }
  button.secondary { background:#1e293b; border-color:#334155; }
  button:hover { opacity:0.92; }
  canvas { width:100%; max-height:430px; background:#050811; border:1px dashed #334155; border-radius:8px; cursor:crosshair; }
  table { width:100%; border-collapse:collapse; font-size:12px; }
  th, td { text-align:left; padding:7px 6px; border-bottom:1px solid #1e293b; }
  th { color:var(--muted); }
  pre { background:#080d1a; padding:10px; border-radius:6px; font-size:12px; max-height:190px; overflow:auto; border:1px solid #1e293b; }
</style>
</head>
<body>
<header>
  <div>
    <strong style="font-size:18px;">GliHub 3.0 · Edge-YOLO26 独立边缘计算节点</strong>
    <span id="nodeLabel" style="margin-left:10px;color:var(--muted);font-size:13px;">Loading...</span>
  </div>
  <div style="display:flex;gap:8px;">
    <span id="precBadge" class="badge">INT8</span>
    <span id="centerBadge" class="badge warn">中心离线 (SQLite 本地续传中)</span>
  </div>
</header>

<div class="kpis">
  <div class="kpi"><div class="lbl">边缘推理吞吐 (FPS)</div><div class="val" id="kpiFps">--</div></div>
  <div class="kpi"><div class="lbl">单帧平均延迟</div><div class="val" id="kpiMs">-- ms</div></div>
  <div class="kpi"><div class="lbl">进程常驻内存 (RSS)</div><div class="val" id="kpiMem">-- MB</div></div>
  <div class="kpi"><div class="lbl">SQLite 待补传 / 已同步</div><div class="val" id="kpiQueue">0 / 0</div></div>
</div>

<div class="grid">
  <div class="card">
    <h3>视觉四任务实时调试 & 电子围栏 (Polygon ROI) 框选</h3>
    <div class="row">
      <select id="taskSel">
        <option value="detect">Detect (无NMS安全帽/违章检测)</option>
        <option value="pose">Pose (高空/跌倒姿态关键点)</option>
        <option value="seg">Seg (跑冒滴漏实例掩码)</option>
        <option value="obb">OBB (旋转框仪表/越线)</option>
      </select>
      <select id="sampleSel"><option value="">-- 选择内置校准样本 --</option></select>
      <input type="file" id="fileInp" accept="image/*" style="max-width:190px;" />
      <button onclick="runInfer(false)">单帧推理</button>
      <button class="secondary" onclick="runInfer(true)">推理并写入断网队列</button>
    </div>
    <div class="row">
      <span style="font-size:12px;color:var(--muted);">在画布点击添加多边形 ROI 顶点（≥3 点生效）：</span>
      <button class="secondary" onclick="clearRoi()">重置全画幅 ROI</button>
      <button onclick="saveRoi()">保存 ROI 围栏</button>
    </div>
    <canvas id="viewCanvas" width="800" height="480"></canvas>
  </div>

  <div class="card">
    <h3>硬件后端与 SQLite 断网续传队列 (WAL Outbox)</h3>
    <pre id="rtJson">加载中...</pre>
    <div class="row" style="justify-content:space-between;margin-top:12px;">
      <strong style="font-size:13px;color:var(--accent);">最近本地缓存告警</strong>
      <button class="secondary" onclick="flushQueue()">立即尝试向中心补传</button>
    </div>
    <table>
      <thead><tr><th>UUID</th><th>任务</th><th>捕获时间</th><th>状态</th><th>重试</th></tr></thead>
      <tbody id="qBody"></tbody>
    </table>
  </div>
</div>

<script>
let roiPts = [];
let bgImg = null;
const canvas = document.getElementById('viewCanvas');
const ctx = canvas.getContext('2d');

canvas.addEventListener('click', (e) => {
  const rect = canvas.getBoundingClientRect();
  const nx = Number(((e.clientX - rect.left) / rect.width).toFixed(3));
  const ny = Number(((e.clientY - rect.top) / rect.height).toFixed(3));
  roiPts.push([nx, ny]);
  redrawCanvas();
});

function redrawCanvas() {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  if (bgImg) ctx.drawImage(bgImg, 0, 0, canvas.width, canvas.height);
  if (roiPts.length > 0) {
    ctx.strokeStyle = '#00e5ff';
    ctx.lineWidth = 2;
    ctx.beginPath();
    roiPts.forEach((p, i) => {
      const x = p[0] * canvas.width, y = p[1] * canvas.height;
      if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      ctx.fillStyle = '#00e5ff';
      ctx.fillRect(x - 3, y - 3, 6, 6);
    });
    if (roiPts.length >= 3) ctx.closePath();
    ctx.stroke();
  }
}

function clearRoi() {
  roiPts = [[0.02,0.02],[0.98,0.02],[0.98,0.98],[0.02,0.98]];
  saveRoi();
}

async function saveRoi() {
  if (roiPts.length < 3) { alert('请至少点击 3 个顶点构成多边形围栏'); return; }
  await fetch('/api/config/roi', {
    method: 'POST',
    headers: {'Content-Type':'application/json'},
    body: JSON.stringify({channel_code:'cam-tank-01', roi_polygon: roiPts, task_type: document.getElementById('taskSel').value})
  });
  await refreshStatus();
}

async function loadSamples() {
  const r = await fetch('/api/samples');
  const d = await r.json();
  const sel = document.getElementById('sampleSel');
  (d.samples || []).forEach(s => {
    const opt = document.createElement('option');
    opt.value = s; opt.textContent = s;
    sel.appendChild(opt);
  });
}

async function runInfer(enqueue) {
  const fd = new FormData();
  fd.append('task_type', document.getElementById('taskSel').value);
  fd.append('enqueue', enqueue ? 'true' : 'false');
  const fileEl = document.getElementById('fileInp');
  const sample = document.getElementById('sampleSel').value;
  if (fileEl.files.length > 0) fd.append('file', fileEl.files[0]);
  else if (sample) fd.append('sample_name', sample);
  const r = await fetch('/api/infer/test', {method:'POST', body: fd});
  const d = await r.json();
  if (d.annotated_b64) {
    const im = new Image();
    im.onload = () => { bgImg = im; roiPts = []; redrawCanvas(); };
    im.src = 'data:image/jpeg;base64,' + d.annotated_b64;
  }
  document.getElementById('rtJson').textContent = JSON.stringify({
    latency_ms: d.latency_ms,
    violations_count: d.violations_count,
    roi_filtered_out: d.roi_filtered_out,
    queued_alert_uuid: d.queued_alert_uuid,
    detections: d.detections
  }, null, 2);
  await refreshStatus();
}

async function flushQueue() {
  await fetch('/api/queue/flush', {method:'POST'});
  await refreshStatus();
}

async function refreshStatus() {
  const [hr, qr] = await Promise.all([fetch('/api/health'), fetch('/api/queue')]);
  const h = await hr.json(), q = await qr.json();
  document.getElementById('nodeLabel').textContent = `${h.node_name} (${h.node_code}) · ${h.runtime.chip_model}`;
  document.getElementById('precBadge').textContent = `${(h.runtime.precision_mode||'int8').toUpperCase()} · ${h.runtime.active_provider}`;
  const cb = document.getElementById('centerBadge');
  cb.textContent = h.center_online ? `中心已连接 (${h.center_url})` : `中心离线 · SQLite 本地续传保护中`;
  cb.className = 'badge ' + (h.center_online ? 'ok' : 'warn');
  document.getElementById('kpiFps').textContent = h.metrics.avg_infer_fps || '--';
  document.getElementById('kpiMs').textContent = (h.metrics.avg_latency_ms || '--') + ' ms';
  document.getElementById('kpiMem').textContent = h.metrics.rss_memory_mb + ' MB';
  document.getElementById('kpiQueue').textContent = `${q.pending} / ${q.synced}`;
  const tbody = document.getElementById('qBody');
  tbody.innerHTML = (q.recent || []).slice(0, 8).map(it =>
    `<tr><td>${it.alert_uuid.slice(0,13)}</td><td>${it.task_type}</td><td>${it.captured_at.slice(11,19)}</td><td>${it.status}</td><td>${it.retry_count}</td></tr>`
  ).join('');
}

loadSamples();
refreshStatus();
setInterval(refreshStatus, 4000);
</script>
</body>
</html>
"""


def create_edge_app(config_path: Optional[Path] = None, start_loops: bool = True) -> FastAPI:
    cfg_mgr = ConfigManager(config_path)
    pipeline = EdgePipelineService(cfg_mgr)

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        if start_loops:
            await pipeline.start_background_loops()
        try:
            yield
        finally:
            if start_loops:
                await pipeline.stop_background_loops()

    app = FastAPI(
        title="GliHub 3.0 Edge-YOLO26 Autonomous Node",
        version="3.0.0",
        lifespan=lifespan,
    )
    app.state.pipeline = pipeline
    app.state.cfg_mgr = cfg_mgr

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/", response_class=HTMLResponse)
    async def debug_ui() -> str:
        return DEBUG_HTML

    @app.get("/api/health")
    async def api_health() -> Dict[str, Any]:
        return pipeline.health_snapshot()

    @app.get("/api/config")
    async def api_config() -> Dict[str, Any]:
        return cfg_mgr.config.to_dict()

    @app.post("/api/config/roi")
    async def api_update_roi(req: RoiUpdateRequest) -> Dict[str, Any]:
        ch = cfg_mgr.update_channel_roi(
            channel_code=req.channel_code,
            roi_polygon=req.roi_polygon,
            task_type=req.task_type,
            conf_threshold=req.conf_threshold,
        )
        return {"updated": True, "config_version": cfg_mgr.config.config_version, "channel": ch}

    @app.get("/api/samples")
    async def api_samples() -> Dict[str, Any]:
        calib_dir = cfg_mgr.base_dir.parent / "data" / "calib_samples"
        names = (
            sorted([p.name for p in calib_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
            if calib_dir.exists()
            else []
        )
        return {"samples": names[:25]}

    @app.post("/api/infer/test")
    async def api_infer_test(
        task_type: str = Form("detect"),
        enqueue: bool = Form(False),
        sample_name: str = Form(""),
        file: Optional[UploadFile] = File(None),
    ) -> Dict[str, Any]:
        img_bgr: Optional[np.ndarray] = None
        if file is not None:
            raw = await file.read()
            arr = np.frombuffer(raw, dtype=np.uint8)
            img_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
        elif sample_name:
            calib_file = (cfg_mgr.base_dir.parent / "data" / "calib_samples" / Path(sample_name).name).resolve()
            if calib_file.exists():
                img_bgr = cv2.imread(str(calib_file))
        else:
            calib_dir = cfg_mgr.base_dir.parent / "data" / "calib_samples"
            if calib_dir.exists():
                candidates = sorted([p for p in calib_dir.iterdir() if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
                if candidates:
                    img_bgr = cv2.imread(str(candidates[0]))

        if img_bgr is None:
            raise HTTPException(status_code=400, detail="No valid image uploaded or found in data/calib_samples")

        return pipeline.process_frame(
            img_bgr,
            task_override=task_type,
            enqueue_alert=enqueue,
            force_enqueue=enqueue,
        )

    @app.get("/api/queue")
    async def api_queue() -> Dict[str, Any]:
        return pipeline.queue.stats()

    @app.post("/api/queue/flush")
    async def api_queue_flush() -> Dict[str, Any]:
        return await pipeline.flush_outbox_once(force=True)

    @app.post("/api/ota/apply")
    async def api_ota_apply(req: OtaRequest) -> Dict[str, Any]:
        return await pipeline.ota.apply_ota(
            download_url=req.download_url,
            target_filename=req.target_filename,
            expected_sha256=req.expected_sha256,
        )

    return app
