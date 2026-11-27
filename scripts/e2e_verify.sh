#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
echo "================================================================"
echo " GliHub 2.0 - AI-EHS 全链路端到端自动化验收脚本"
echo " 链路: yolov5target-main -> VLM复核 -> 法规溯源 -> 隐患工单 -> 动态评价报告 -> 事故推演 -> 复检闭环"
echo "================================================================"

echo "[1/3] 检查 FastAPI ai-service (:8090) 健康状态..."
curl -fsS http://127.0.0.1:8090/api/v1/health | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  -> status={d[\"status\"]}, device={d[\"optimal_device\"]}, models={[m[\"model_code\"] for m in d[\"models\"]]}')
assert d['status'] == 'ok'
"

echo "[2/3] 执行 Spring Boot + PostgreSQL + Redis + ai-service 全链路闭环集成测试..."
cd "$ROOT_DIR/backend"
if [ -d "/opt/homebrew/opt/openjdk@11" ]; then
  export JAVA_HOME="/opt/homebrew/opt/openjdk@11"
  export PATH="$JAVA_HOME/bin:$PATH"
fi
mvn test -Dtest=GliHubV2ClosedLoopE2ETest

echo "[3/3] 执行前端 Vue 3 生产包构建语法核验..."
cd "$ROOT_DIR/frontend"
npm run build > /dev/null
rm -rf dist

echo "================================================================"
echo " ✅ GliHub 2.0 全链路端到端验收测试全部通过 (ALL PASSED)!"
echo "================================================================"
