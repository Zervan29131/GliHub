# GliHub 2.0 — AI 驱动的工业安全感知、动态评价与应急决策一体化平台

GliHub 2.0 在既有「Spring Boot + Vue 3 + PostgreSQL + Redis」安全评价底座之上完成智能化架构跃迁，新增独立的 **Python FastAPI 多模态视觉与智能体微服务（`ai-service`）**，无缝纳管本地自训 **`yolov5target-main`** 权重，构建起 **「视觉感知告警 → VLM 多模态复核 → 法规知识库溯源 → 隐患工单派发与 AI 复查 → 动态安全评价报告 → 事故情景应急推演」** 全自动化闭环。

---

## 一、系统总体架构与目录结构

```text
GliHub/
├── backend/                     # Spring Boot 2.5.15 业务中台 (com.glihub)
│   ├── Dockerfile               # 后端多阶段构建镜像
│   └── src/
│       ├── main/java/com/glihub/ehs/ # AI 熔断客户端、闭环编排服务、WebSocket 广播 (/ws/alerts)
│       └── test/java/com/glihub/ehs/ # 全链路端到端自动化验收测试 (GliHubV2ClosedLoopE2ETest)
├── ai-service/                  # Python FastAPI 视觉推理、VLM 复核、RAG 与决策智能体服务 (:8090)
│   ├── Dockerfile               # AI 微服务容器镜像
│   ├── .env.example             # OpenAI-Compatible 模型端点解耦配置模板
│   ├── adapters/                # 统一视觉插件层: yolov5_local / yolo26 / rfdetr / yoloe
│   ├── vlm/                     # 第二阶段多模态复核 (Qwen3-VL / InternVL3 / 离线规则兜底)
│   ├── rag/                     # PDF/国标条款解析切分 + pgvector/混合检索引擎 + SSE 流式问答
│   └── agents/                  # Dow/LEC 参数依据推荐、评价报告生成与《现场应急处置行动卡》推演
├── frontend/                    # Vue 3 + Vite + Element Plus 前端
│   ├── Dockerfile & nginx.conf  # 前端容器镜像与 REST/SSE/WebSocket 反向代理
│   └── src/
│       ├── components/EhsAiCopilot/  # 全局悬浮「GliHub 安全合规助手」抽屉 + WebSocket 告警弹窗
│       └── views/               # 态势指挥舱 + 五大业务域核心页面
├── yolov5target-main/           # 存量自训 YOLOv5 安全帽检测模型与权重（无侵入挂载调用）
├── sql/
│   ├── glihub.sql               # 1.0 核心 RBAC 与基础业务表初始化脚本
│   └── glihub_v2_upgrade.sql    # 2.0 增量升级脚本（9 张 ehs_* 表、pgvector 向量列与五大业务域菜单）
├── scripts/
│   └── e2e_verify.sh            # 一键全链路端到端自动化测试验收脚本
└── docker-compose.yml           # 一键容器化编排 (pgvector:pg16 + Redis + ai-service + backend + frontend)
```

---

## 二、五大核心业务域与模型矩阵

| 业务域 / 模块 | 核心功能亮点 | 接入开源模型矩阵（支持本地私有化或兼容 API） |
| :--- | :--- | :--- |
| **全域安全态势指挥舱** | 三大场所（生产/储存/公辅）风险热力、厂区危险源与摄像头电子沙盘、实时视觉告警流、隐患闭环率 | WebSocket `/ws/alerts` 秒级推送 |
| **智能视觉与隐患闭环** | Stage-1 毫秒级框选 + Stage-2 VLM 二次复核防误报；高危违章自动转隐患工单；整改后上传复查图经 AI 自动核验销项 | 存量 `yolov5target-main`（安全帽+人员双检反推） / `Ultralytics YOLO26` / `RF-DETR` / `YOLOE`（自然语言提示词零样本） + `Qwen3-VL` / `InternVL3` |
| **AI 动态安全评价引擎** | **100% 保留 Dow F&EI、LEC、TNT 当量、SCL 确定性数学公式精度**；新增未闭环隐患触发 LEC 重评预警、AI 参数依据推荐、**TNT 冲击波半径（$R_1..R_4$）平面同心圆叠加**、评价报告 `.doc`/`.md` 导出 | `DeepSeek-V3.2 / R1` 或 `Qwen3.5`（严谨协同，绝不替代确定性公式） |
| **全息危险源与应急推演** | 「场所 → 危险源（GB 18218 $R$ 值） → 设备 → 摄像头 → 人员 → 法规」六维全息图谱；联动泄漏量与风向秒级生成《现场应急处置行动卡》 | TNT 空间波及计算 + 应急战术智能体 |
| **EHS 法规标准知识库** | PDF/国标/SDS 条款自动切分与向量化入库；SCL 国标推荐、隐患法条自动引用、全局悬浮 SSE 流式合规问答 | PostgreSQL `pgvector` + `Qwen3-Embedding` + `DeepSeek-OCR 2` / `pypdf` |

---

## 三、环境变量配置说明（OpenAI-Compatible 零锁定）

所有 VLM、LLM 与 Embedding 均严格遵循 **OpenAI-Compatible API** 规范，可在 [ai-service/.env](ai-service/.env.example) 或根目录 [.env](.env.example) 中灵活配置：

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `DB_URL` | `jdbc:postgresql://localhost:5432/glihub` | Spring Boot PostgreSQL 连接串 |
| `AI_SERVICE_URL` | `http://127.0.0.1:8090` | Spring Boot 调用 `ai-service` 地址（离线自动熔断回退） |
| `YOLOV5_REPO_DIR` | `../yolov5target-main` | 存量 YOLOv5 代码与 `.pt` 权重根目录 |
| `VLM_BASE_URL` / `VLM_MODEL` | `http://localhost:11434/v1` / `qwen2.5vl:7b` | 视觉复核端点（支持本地 Ollama / vLLM / 云端 Qwen3-VL、InternVL3；未配置时自动启用工业规则复核兜底） |
| `LLM_BASE_URL` / `LLM_MODEL` | `http://localhost:11434/v1` / `qwen3:8b` | 安全评价报告与合规问答端点（支持 DeepSeek-V3.2/R1、Qwen3.5） |
| `EMBEDDING_BASE_URL` | 空（内置 1024 维确定性混合检索） | 可配置 `Qwen/Qwen3-Embedding-0.6B` `/v1/embeddings` 端点 |

---

## 四、快速启动方式

### 方式一：Docker Compose 全栈一键编排（推荐生产/演示）

内置 `pgvector/pgvector:pg16`，首次启动会自动按序执行 [sql/glihub.sql](sql/glihub.sql) 与 [sql/glihub_v2_upgrade.sql](sql/glihub_v2_upgrade.sql)：

```bash
cp .env.example .env
docker compose up -d --build
```
启动完成后访问 `http://localhost:8088`（默认管理员账号：`admin` / `admin123`）。

### 方式二：本地宿主机开发启动（macOS / Linux）

1. **初始化 PostgreSQL 数据库**：
   ```bash
   createdb -U postgres -E UTF8 glihub
   psql -U postgres -d glihub -f sql/glihub.sql
   psql -U postgres -d glihub -f sql/glihub_v2_upgrade.sql
   ```
2. **启动 Python `ai-service` 微服务（`:8090`）**：
   ```bash
   cd ai-service
   python3.11 -m venv .venv
   ./.venv/bin/pip install -r requirements.txt
   ./.venv/bin/python main.py
   ```
3. **编译并启动 Spring Boot 后端中台（默认 `:8080`，如端口占用可设 `SERVER_PORT=8081`）**：
   ```bash
   cd backend
   mvn clean package -DskipTests
   java -jar target/glihub-backend.jar
   ```
4. **启动 Vue 3 前端开发服务**：
   ```bash
   cd frontend
   npm install
   VITE_PROXY_TARGET=http://localhost:8080 npx vite --port 5173
   ```

---

## 五、端到端全链路自动化验收

在 PostgreSQL、Redis 与 `ai-service` 启动状态下，执行一键验收脚本：

```bash
bash scripts/e2e_verify.sh
```

该脚本将自动跑通并断言以下完整业务闭环：
1. 调用 `yolov5target-main` 权重检出人员未佩戴安全帽违章框；
2. 触发 VLM 二次复核判定真实高危隐患，并由 RAG 自动匹配引用《安全生产法》条款；
3. 自动派发 `OPEN` 状态的隐患排查治理工单；
4. 自动触发所属作业区 LEC 动态风险重评预警与 AI 参数推荐；
5. 生成并归档结构化《AI 安全评价报告》及重大危险源《现场应急处置行动卡》；
6. 提交复查样本照片经 AI 自动核验通过，将隐患工单流转至 `CLOSED` 销项闭环。

---

## 六、开源协议

本项目基于 [MIT License](LICENSE) 开源。
