# GliHub — 安全评价与安全信息管理系统

GliHub 是一套面向工业与危化品企业的**安全评价管理**与**安全信息管理**一体化 Web 平台，基于 **Spring Boot + Vue 3 + Element Plus + PostgreSQL + Redis** 构建，采用清晰的前后端分离单体目录结构。

---

## 一、核心功能模块

### 1. 安全评价管理
- **多场所安全评价单元**：覆盖**生产场所**、**储存场所**、**公辅场所**三类作业场所及下属作业区域动态切换。
- **四大安全评价计算程序**：
  - **道氏火灾、爆炸危险指数法（Dow F&EI）**：自动计算单元危险系数 $F_3$、初始及补偿后火灾爆炸指数 $F\&EI$、暴露区域半径与面积，并输出危险等级评定。
  - **作业条件危险性分析法（LEC）**：基于事故可能性 $L$、暴露频繁程度 $E$、事故后果 $C$ 计算风险分值 $D = L \times E \times C$，自动判定 1~5 级风险及整改管控措施。
  - **重大危险源事故后果模拟法（TNT 当量法）**：模拟可燃介质蒸气云爆炸，自动计算 TNT 当量 $W_{TNT}$ 及死亡半径 $R_1$、重伤半径 $R_2$、轻伤半径 $R_3$、财产损失半径 $R_4$ 与警戒疏散距离。
  - **安全检查表法（SCL）**：内置生产、储存、公辅场所国家法规与标准检查项模板，支持自定义增删检查项、合规率实时统计与 CSV 报表导出。
- **危险源辨识评估与隐患排查治理**：支持工序危险源风险评估及现场隐患排查台账管理。

### 2. 安全信息管理
- **基础信息管理**：作业区层级树管理、特种与安全设备基础台账管理、从业人员与安全员档案管理。
- **危险源详情档案**：重点危险源理化危险特性、风险等级及现场应急处置要点检索与维护。
- **安全知识库（法律文献与技术标准）**：集中管理《安全生产法》《危险化学品安全管理条例》、GB 18218、GB 30871 等安全生产法律法规、国家技术标准及企业规章制度。
- **应急预案管理**：专项现场应急救援措施编制、预案摘要核验及应急预案表导出。

### 3. 智能视觉监控与基础权限支撑
- **智能视觉监控**：支持 YOLO 检测模型管理与作业现场图像安全检测对接（可选配本地视觉推理服务）。
- **最小公共权限底座**：基于 JWT + Spring Security + Redis 的登录鉴权、图形验证码、角色菜单权限（RBAC）、数据范围过滤及数据字典配置。

---

## 二、目录结构

```text
GliHub/
├── backend/                        # Spring Boot 后端单体工程 (com.glihub)
│   ├── pom.xml                     # Maven 配置文件
│   └── src/main/
│       ├── java/com/glihub/
│       │   ├── GliHubApplication.java
│       │   ├── common/             # 通用常量、注解、工具类与基础实体
│       │   ├── framework/          # Security 鉴权、JWT Token、Redis、全局异常处理
│       │   ├── system/             # 领域实体、Mapper 接口与业务 Service
│       │   └── web/controller/     # RESTful API 控制器
│       └── resources/
│           ├── application.yml     # 主配置（服务端口、Redis、JWT、MyBatis、PostgreSQL 分页）
│           ├── application-druid.yml # PostgreSQL Druid 数据源配置
│           ├── logback.xml         # 日志配置
│           └── mapper/system/      # PostgreSQL 方言 MyBatis Mapper XML (13 个)
├── frontend/                       # Vue 3 + Vite + Element Plus 前端工程
│   ├── package.json
│   ├── vite.config.js              # 开发代理 (/dev-api -> http://localhost:8080)
│   └── src/
│       ├── api/                    # 后端接口封装
│       ├── components/             # 公共 UI 组件
│       ├── layout/                 # 主框架布局与导航栏
│       ├── router/                 # 路由配置
│       ├── store/                  # Pinia 状态管理
│       ├── utils/                  # 请求拦截与通用工具函数 (glihub.js)
│       └── views/                  # 业务视图（安全评价、安全信息、系统基础设置）
├── sql/
│   └── glihub.sql                  # PostgreSQL 数据库表结构与初始化数据脚本
└── README.md
```

---

## 三、技术栈与环境要求

| 组件 | 版本要求 | 说明 |
| :--- | :--- | :--- |
| **JDK** | 1.8 / 11 | Spring Boot 2.5.15 运行环境 |
| **Maven** | 3.6+ | 后端依赖管理与打包 |
| **PostgreSQL** | 12+ | 核心业务关系型数据库（UTF-8 编码） |
| **Redis** | 5.0+ | 登录会话令牌、图形验证码与字典缓存 |
| **Node.js** | 16.x ~ 22.x+ | 前端构建运行环境（推荐搭配 npm 8+） |

---

## 四、快速启动指南

### 1. 初始化 PostgreSQL 数据库

创建 UTF-8 编码的 `glihub` 数据库并执行初始化脚本 [sql/glihub.sql](sql/glihub.sql)：

```bash
createdb -U postgres -E UTF8 glihub
psql -U postgres -d glihub -f sql/glihub.sql
```

### 2. 配置环境变量并启动后端

后端在 [application.yml](backend/src/main/resources/application.yml) 与 [application-druid.yml](backend/src/main/resources/application-druid.yml) 中已支持环境变量注入（未设置时自动回退至本地默认值）：

| 环境变量 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `SERVER_PORT` | `8080` | 后端 HTTP 服务端口 |
| `DB_URL` | `jdbc:postgresql://localhost:5432/glihub` | PostgreSQL JDBC 连接串 |
| `DB_USERNAME` | `postgres` | 数据库用户名 |
| `DB_PASSWORD` | `postgres` | 数据库密码 |
| `REDIS_HOST` | `localhost` | Redis 主机地址 |
| `REDIS_PORT` | `6379` | Redis 端口 |
| `REDIS_PASSWORD` | 空字符串 | Redis 密码（无密码留空即可） |
| `GLIHUB_PROFILE` | `./upload` | 本地文件上传存储目录 |

确保本地 PostgreSQL 与 Redis 已启动后，进入 `backend` 目录编译并运行：

```bash
cd backend

# 按需覆盖本地数据库或 Redis 密码
export DB_URL="jdbc:postgresql://localhost:5432/glihub"
export DB_USERNAME="postgres"
export DB_PASSWORD="your_pg_password"

mvn clean package -DskipTests
java -jar target/glihub-backend.jar
```

### 3. 安装依赖并启动前端

打开新终端进入 `frontend` 目录：

```bash
cd frontend
npm install
npm run dev
```

启动成功后浏览器访问 `http://localhost:80`（如无 80 端口权限可在 [vite.config.js](frontend/vite.config.js) 中改为 `5173` 或 `3000`）。生产环境打包可执行：

```bash
npm run build
```

---

## 五、默认登录账号

| 角色 | 账号 | 初始密码 | 权限范围 |
| :--- | :--- | :--- | :--- |
| **超级管理员** | `admin` | `admin123` | 全平台安全评价、安全信息管理与系统基础设置权限 |
| **安全评价员** | `operator` | `admin123` | 安全评价计算、危险源管理、设备台账与安全知识库权限 |

---

## 六、开源协议

本项目基于 [MIT License](LICENSE) 开源。
