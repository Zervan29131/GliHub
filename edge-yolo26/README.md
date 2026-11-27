# GliHub 3.0 — `edge-yolo26` 独立边缘计算节点

`edge-yolo26/` 是 **GliHub 3.0** 的零中心依赖轻量级边缘视觉推理服务，专为无独立显卡设备（树莓派 5、RK3588、Jetson Orin Nano、工控机及 macOS / Windows / Linux 办公终端）设计。

## 核心特性
- **零中心依赖**：无需安装 PostgreSQL、Valkey 或 Spring Boot，仅凭 `onnxruntime` + 内置 `SQLite WAL` 即可长期独立自治运行。
- **单框架四大任务无 NMS 推理**：原生支持 **Ultralytics YOLO26** 端到端无 NMS 模型（`detect` 目标检测、`pose` 姿态关键点、`seg` 实例分割、`obb` 旋转框）与存量 `yolov5_helmet.int8.onnx` 安全帽权重空间耦合研判。
- **低精度与算力自适应**：自动路由硬件后端（CUDA / DirectML / OpenVINO / CoreML / ARM64·AVX2 INT8），自适应限制 CPU 线程与静止画面动态降帧（`0.5 FPS` 休眠 → 运动触发瞬时满帧）。
- **SQLite 环形缓存断网续传**：中心网络中断时告警加密暂存本地 `edge_alert_outbox`，网络恢复后按 `X-Edge-Token` 自动批量补传（`alertUuid` 幂等去重）。
- **SHA256 模型 OTA 热更新 & `:8091` 微型调试台**：内置单页可视化 Canvas 电子围栏（Polygon ROI）绘制与单图/流式实时测试台。

## 快速启动（纯 CPU INT8 模式）

```bash
cd edge-yolo26
# 1. 创建极简运行时环境（无需安装数 GB PyTorch）
uv venv --python 3.12
uv pip install -r pyproject.toml

# 2. （首次可选）若 ../data/models/ 尚未生成量化模型，选装导出器一键生成 INT8 ONNX
uv pip install -r pyproject.toml --extra export
./.venv/bin/python scripts/export_int8_models.py

# 3. 运行纯 CPU 低精度与断网续传基准测试
./.venv/bin/python benchmark_cpu.py

# 4. 启动边缘自治节点与 :8091 微型 Web 调试台
./.venv/bin/python main.py
```

启动后浏览器访问 `http://127.0.0.1:8091` 即可在线框选电子围栏、测试四大视觉任务与查看断网续传队列。
