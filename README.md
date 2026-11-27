# GliHub 3.0 — 端云协同、插件化选装、低算力友好的 AI 工业安全风控与应急决策平台

**GliHub 3.0** 面向石油化工、危化品储运与制造企业，在 100% 保留四大确定性安全评价算法（**Dow F&EI 道氏火灾爆炸指数法**、**LEC 作业条件危险性分析法**、**TNT 当量事故后果模拟法**、**SCL 安全检查表法**）严谨性的基础上，全面升级为**「7 层开源 AI 模型按需选装 + 全链路无独显低精度量化推理 + 独立 YOLO26 边缘自治节点 + 三端单目录无缝迁移」**的新一代智能 EHS 底座。

---

## 一、GliHub 3.0 四大核心能力跃迁

1. **7 层开源 AI 模型全模块化“选装”架构（0 选装亦 100% 可用）**
   - 每个 AI 模块均通过 `ai-service/plugins/mod_*/manifest.json` 与 `uv sync --extra <mod>` 实现安装级与运行级双解耦；**即使不安装任何 AI 插件，核心安全评价计算、台账管理与 RBAC 权限依然 100% 独立稳定运行**。
   - **7 大插件矩阵**：`mod-yolov5`（存量 `best.pt` 校准静态 INT8）、`mod-yolo26`（原生无 NMS 四任务 INT8）、`mod-rfdetr`（GPU FP16 高精度检测）、`mod-yoloe`（中文开放词汇零样本排查）、`mod-vlm`（Qwen3-VL/InternVL3 GGUF `Q4_K_M` 二次防误报复核）、`mod-llm-rag`（DeepSeek/Qwen + PostgreSQL `pgvector` 法规溯源与报告推演）、`mod-ocr`（DeepSeek-OCR 2 / PP-OCR INT8 法规票证解析）。
2. **无独显设备全链路低精度量化（`cpu-int8` / `local-q4` / `gpu-pro`）**
   - 内置硬件加速自探测（`CUDA` → `Apple Silicon` → `DirectML` → `OpenVINO` → `ARM64/AVX2 CPU INT8`），自适应限制 CPU 线程与静止画面动态降帧。
   - 8GB 普通无独显笔记本或 2C4G 轻量云主机在 `cpu-int8` 模式下，单帧无 NMS 视觉推理仅 **`~26 ms`（37+ FPS）**，边缘节点常驻内存 **`~306 MB`**。
3. **完全独立的 Ultralytics YOLO26 边缘计算节点（`edge-yolo26/`）**
   - **零中心依赖**：无需 PostgreSQL、Valkey 或 Spring Boot，单框架覆盖 `detect` / `pose` / `seg` / `obb` 四大任务，内置 **SQLite WAL 环形缓存断网续传**、**多边形电子围栏（Polygon ROI）**、**SHA256 量化模型 OTA 热更新**及 `:8091` 微型可视化调试台。
4. **最新 LTS 技术栈与 macOS / Windows / Linux 无缝单目录迁移**
   - **后端中台（`backend/`）**：**OpenJDK 25 LTS**（紧凑对象头 `-XX:+UseCompactObjectHeaders` + 虚拟线程，向下兼容 JDK 21 LTS）+ **Spring Boot `4.2.0`** + **HikariCP** + **Flyway**（`V1~V3` 自动建库与平滑升版）+ **OpenAPI 3.1**。
   - **前端工作台（`frontend/`）**：**Node.js 26 LTS** + **Vue `3.5`** + **Vite `6.4`** + **Element Plus** + **Pinia**。
   - **存储与Python引擎**：**PostgreSQL `18` (`pgvector`)** + **Valkey `9.x`**（纯 JSON 无 AutoType 序列化）+ **Python `3.12+` (`uv`)**；所有模型、上传件、快照与卷统一收敛至 `./data/`。

---

## 二、仓库目录结构

```text
GliHub/
├── backend/            # Spring Boot 4.2 + JDK 25 中台 (安全评价引擎 / 边缘接入网关 / Flyway V1~V3)
├── frontend/           # Vue 3.5 + Vite 6 前端 (态势指挥舱 / 边缘ROI框选 / 7插件选装中心 / 动态评价)
├── ai-service/         # FastAPI 模块化 AI 中心服务 (Precision Manager + 7 个可插拔选装插件)
├── edge-yolo26/        # 零中心依赖独立边缘计算节点 (YOLO26 无NMS INT8 + SQLite 断网续传 + :8091 调试台)
├── scripts/
│   └── glihub_cli.py   # macOS / Windows / Linux 跨平台统一管理 CLI (纯标准库)
├── sql/                # PostgreSQL 初始化与增量归档脚本
├── data/               # 统一持久化目录 (models / calib_samples / uploads / edge_snaps / backups)
└── docker-compose.yml  # 多 Profile 跨平台编排 (pg18 + valkey9 + cpu-int8 / local-q4 / edge)
```

---

## 三、三端（macOS / Windows / Linux）快速启动指南

### 方式 A：Docker Compose 一键容器化启动（推荐跨平台迁移）

```bash
cp .env.example .env

# 1. 无独显设备推荐：启动核心平台 + CPU INT8 插件引擎 + 独立边缘节点
docker compose --profile cpu-int8 --profile edge up -d

# 2. 极简 0-AI 纯确定性安全评价与台账模式（最低资源占用）
docker compose up -d

# 3. 16GB+ 内存本地全离线大模型模式（自动拉起 Ollama Q4_K_M 服务）
docker compose --profile local-q4 up -d
```

### 方式 B：本地源码无卡低精度（`cpu-int8`）开发启动

```bash
# 1. 环境与硬件加速自检
python3 scripts/glihub_cli.py check-env

# 2. 按需选装 AI 插件（传 --modules none 可验证 0 插件模式）
python3 scripts/glihub_cli.py install --modules cpu-int8 --with-edge

# 3. 一键导出并生成 YOLO26n 与自训安全帽模型的静态 INT8 (QDQ) ONNX 权重
python3 scripts/glihub_cli.py quantize

# 4. 分别启动中心 AI 服务(:8090)、边缘自治节点(:8091)、JDK 25 中台(:8080/8081) 与前端(:5173)
cd ai-service && ./.venv/bin/python main.py
cd edge-yolo26 && ./.venv/bin/python main.py --port 8091
cd backend && ./mvnw spring-boot:run
cd frontend && npm install --legacy-peer-deps && npm run dev
```

---

## 四、独立边缘盒子（`edge-yolo26/`）单独拆分部署

无需复制整个仓库，一键打包即可拷入树莓派 5、RK3588、工控机或任意电脑独立运行：

```bash
# 在开发机生成包含 INT8 权重的便携部署包 (~19 MB)
python3 scripts/glihub_cli.py edge-pack

# 在边缘设备上解压即跑（断网自动缓存至本地 SQLite，联网自动续传中心）
tar -xzf data/backups/glihub-edge-yolo26-standalone.tar.gz
cd edge-yolo26 && uv sync && ./.venv/bin/python main.py
# 浏览器打开 http://127.0.0.1:8091 即可绘制电子围栏与实时调试
```

---

## 五、单文件跨机备份迁移与端到端验收

```bash
# 一键导出跨平台迁移快照包 (含 ./data 量化权重、抓拍图与数据库快照)
python3 scripts/glihub_cli.py backup

# 在新机器 (macOS / Windows / Linux) 一键恢复
python3 scripts/glihub_cli.py restore data/backups/glihub_v3_snapshot_xxx.tar.gz

# 执行纯 CPU (cpu-int8) 端云协同全闭环自动化验收
python3 scripts/glihub_cli.py e2e
```

- **默认管理员账号**：`admin` / `admin123`
- **OpenAPI 3.1 接口文档**：`http://localhost:8080/swagger-ui.html`（`/v3/api-docs`）
