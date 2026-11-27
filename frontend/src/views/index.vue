<template>
  <div class="app-container command-center">
    <!-- 顶部态势总控横幅 (GliHub 3.0) -->
    <div class="cockpit-banner">
      <div>
        <div class="cockpit-title">GliHub 3.0 端云协同 AI 工业安全态势指挥舱（Edge-Cloud Command Center）</div>
        <div class="cockpit-sub">
          YOLO26 独立边缘自治 · 7 层插件选装 · CPU INT8 低精度推理 · 确定性安全评价 · 应急决策一体化平台
        </div>
      </div>
      <div class="cockpit-status">
        <el-tag :type="aiOnline ? 'success' : 'warning'" effect="dark">
          中心引擎：{{ aiOnline ? `${deployProfile.toUpperCase()} (${activePluginsCount}/7 插件启用)` : '本地确定性容灾模式' }}
        </el-tag>
        <el-tag type="primary" effect="dark" style="cursor: pointer" @click="go('/vision-loop/edge')">
          边缘节点：{{ overview.edgeNodes.length }} 台在线 ({{ topEdgeFps }} FPS)
        </el-tag>
        <el-button size="small" type="primary" icon="VideoCamera" @click="go('/vision-loop/workbench')">
          视觉研判台
        </el-button>
        <el-button size="small" type="success" icon="Connection" @click="go('/vision-loop/edge')">
          边缘 &amp; ROI
        </el-button>
        <el-button size="small" type="info" icon="SetUp" @click="go('/vision-loop/plugins')">
          模型选装
        </el-button>
        <el-button size="small" type="warning" icon="Cpu" @click="go('/dynamic-eval/evaluate')">
          动态评价
        </el-button>
        <el-button size="small" type="danger" icon="Aim" @click="go('/hazard-emergency/drill')">
          应急推演
        </el-button>
        <el-button size="small" icon="Refresh" :loading="loading" @click="fetchOverview">刷新</el-button>
      </div>
    </div>

    <!-- 核心 KPI 指标卡 -->
    <el-row :gutter="16" class="mb16">
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="kpi-card">
          <div class="kpi-label">纳管重点危险源</div>
          <div class="kpi-value text-danger">{{ overview.hazards.length }} <span class="kpi-unit">处</span></div>
          <div class="kpi-foot">覆盖生产 / 储存 / 公辅三大场所</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="kpi-card">
          <div class="kpi-label">隐患治理闭环率</div>
          <div class="kpi-value text-success">{{ overview.orderClosureRate }}<span class="kpi-unit">%</span></div>
          <el-progress :percentage="overview.orderClosureRate" :stroke-width="6" status="success" :show-text="false" />
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="kpi-card" @click="go('/vision-loop/orders')">
          <div class="kpi-label">待销项隐患工单</div>
          <div class="kpi-value text-warning">{{ overview.openOrders }} <span class="kpi-unit">单</span></div>
          <div class="kpi-foot">累计工单 {{ overview.totalOrders }} 单（点击督办）</div>
        </el-card>
      </el-col>
      <el-col :xs="12" :sm="6">
        <el-card shadow="hover" class="kpi-card" @click="go('/vision-loop/edge')">
          <div class="kpi-label">边缘自治节点 &amp; 特种设备</div>
          <div class="kpi-value text-primary">{{ overview.edgeNodes.length }} <span class="kpi-unit">节点</span> / {{ overview.totalEquipments }} <span class="kpi-unit">套</span></div>
          <div class="kpi-foot">监控点位 {{ overview.cameraPoints.length }} 路 · INT8 断网续传保护中</div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 中部：厂区全域电子态势平面图 + 三大场所风险热力 -->
    <el-row :gutter="16" class="mb16">
      <el-col :xs="24" :lg="15">
        <el-card shadow="never">
          <template #header>
            <div class="section-hdr">
              <span>厂区重大危险源与边缘视觉布防态势电子沙盘</span>
              <span class="sub-note">点击危险源节点可进入全息关联图谱</span>
            </div>
          </template>
          <div class="plant-map-wrap">
            <svg viewBox="0 0 600 340" class="plant-svg">
              <rect x="16" y="16" width="275" height="308" rx="8" fill="#fef0f0" stroke="#f56c6c" stroke-dasharray="5,4" />
              <text x="28" y="38" fill="#c45656" font-size="13" font-weight="bold">生产场所区 (采油 / 合成气管廊)</text>

              <rect x="308" y="16" width="276" height="152" rx="8" fill="#fdf6ec" stroke="#e6a23c" stroke-dasharray="5,4" />
              <text x="320" y="38" fill="#b88230" font-size="13" font-weight="bold">储存场所区 (危化品储罐与甲类库)</text>

              <rect x="308" y="182" width="276" height="142" rx="8" fill="#ecf5ff" stroke="#409eff" stroke-dasharray="5,4" />
              <text x="320" y="204" fill="#337ecc" font-size="13" font-weight="bold">公辅场所区 (变配电 / 空压 / 消防泵房)</text>

              <g v-for="cam in overview.cameraPoints" :key="'cam-' + cam.pointId">
                <circle :cx="cam.mapX * 6" :cy="cam.mapY * 3.4" r="6" fill="#409eff" />
                <text :x="cam.mapX * 6 + 9" :y="cam.mapY * 3.4 + 4" fill="#303133" font-size="10">
                  {{ cam.pointCode }}
                </text>
              </g>

              <g
                v-for="hz in overview.hazards"
                :key="'hz-' + hz.hazardId"
                class="hz-node"
                @click="go(`/hazard-emergency/hologram?hazardId=${hz.hazardId}`)"
              >
                <circle
                  :cx="hz.mapX * 6"
                  :cy="hz.mapY * 3.4"
                  r="18"
                  :fill="hz.riskLevel === '重大风险' ? 'rgba(245,108,108,0.25)' : 'rgba(230,162,60,0.25)'"
                />
                <circle
                  :cx="hz.mapX * 6"
                  :cy="hz.mapY * 3.4"
                  r="9"
                  :fill="hz.riskLevel === '重大风险' ? '#f56c6c' : '#e6a23c'"
                  stroke="#fff"
                  stroke-width="2"
                />
                <text :x="hz.mapX * 6 - 42" :y="hz.mapY * 3.4 - 14" fill="#1f2d3d" font-size="11" font-weight="600">
                  {{ hz.hazardName }}
                </text>
              </g>
            </svg>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="9">
        <el-card shadow="never" class="full-height">
          <template #header>
            <div class="section-hdr">
              <span>生产 / 储存 / 公辅三类场所实时风险热力</span>
            </div>
          </template>
          <div v-for="item in placeCards" :key="item.key" class="place-heat-item">
            <div class="place-heat-top">
              <strong>{{ item.name }}</strong>
              <el-tag :type="item.stat.riskStatus === '高风险预警' ? 'danger' : item.stat.riskStatus === '受控关注' ? 'warning' : 'success'">
                {{ item.stat.riskStatus || '平稳受控' }}
              </el-tag>
            </div>
            <div class="place-heat-metrics">
              <span>危险源：<b>{{ item.stat.hazardCount || 0 }}</b> 处</span>
              <span>未闭环工单：<b>{{ item.stat.openOrderCount || 0 }}</b> 单</span>
              <span>近7日告警：<b>{{ item.stat.recentAlertCount || 0 }}</b> 次</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部：实时视觉复核告警流 + 近期动态安全评价记录 -->
    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card shadow="never">
          <template #header>
            <div class="section-hdr">
              <span>最新端云协同视觉检测 + VLM 二次复核告警流</span>
              <el-button link type="primary" @click="go('/vision-loop/workbench')">进入工作台研判 &gt;</el-button>
            </div>
          </template>
          <el-empty v-if="!overview.recentAlerts.length" description="暂无历史视觉告警，可前往「视觉研判工作台」或「边缘节点」体验 INT8 检测" />
          <el-table v-else :data="overview.recentAlerts" size="small" border>
            <el-table-column label="标注缩略图" width="95" align="center">
              <template #default="{ row }">
                <el-image
                  v-if="row.annotatedImageUrl"
                  :src="resolveUrl(row.annotatedImageUrl)"
                  :preview-src-list="[resolveUrl(row.annotatedImageUrl)]"
                  preview-teleported
                  style="width: 64px; height: 42px; border-radius: 4px"
                  fit="cover"
                />
              </template>
            </el-table-column>
            <el-table-column prop="deptName" label="作业区域" width="120" />
            <el-table-column prop="violationType" label="复核判定" min-width="140" />
            <el-table-column label="等级" width="85" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.severity === 'CRITICAL' || row.severity === 'HIGH' ? 'danger' : row.severity === 'MEDIUM' ? 'warning' : 'success'">
                  {{ row.severity }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="handleStatus" label="闭环状态" width="135" align="center" />
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card shadow="never">
          <template #header>
            <div class="section-hdr">
              <span>近期动态安全评价与报告归档</span>
              <el-button link type="primary" @click="go('/dynamic-eval/eval-records')">查看全部 &gt;</el-button>
            </div>
          </template>
          <el-empty v-if="!overview.recentEvaluations.length" description="尚无归档记录，前往「动态安全评价引擎」执行评价并生成 AI 报告" />
          <el-timeline v-else>
            <el-timeline-item
              v-for="ev in overview.recentEvaluations"
              :key="ev.evalId"
              :timestamp="ev.areaName + ' · ' + ev.evalMethod"
              placement="top"
            >
              <el-tag size="small" type="warning" class="mr8">{{ ev.riskGrade }}</el-tag>
              <span style="font-size: 12px; color: #606266">单号：{{ ev.evalNo }}</span>
            </el-timeline-item>
          </el-timeline>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup name="CommandCenter">
import { getCommandOverview, resolveBackendAssetUrl } from '@/api/ehs'

const router = useRouter()
const loading = ref(false)
const overview = reactive({
  aiEngineHealth: {},
  placeHeatmap: {},
  hazards: [],
  recentAlerts: [],
  totalOrders: 0,
  openOrders: 0,
  orderClosureRate: 100,
  totalEquipments: 0,
  recentEvaluations: [],
  cameraPoints: [],
  edgeNodes: []
})

const aiOnline = computed(() => overview.aiEngineHealth?.status === 'ok')
const deployProfile = computed(() => overview.aiEngineHealth?.deploy_profile || 'cpu-int8')
const activePluginsCount = computed(() => overview.aiEngineHealth?.plugins_active_count ?? 6)
const topEdgeFps = computed(() => {
  if (!overview.edgeNodes.length) return 0
  return overview.edgeNodes[0].current_fps || 37.4
})

const placeCards = computed(() => [
  { key: 'production', name: '生产场所（采油 / 合成气装置区）', stat: overview.placeHeatmap?.production || {} },
  { key: 'storage', name: '储存场所（甲醇罐区 / 甲类危化库）', stat: overview.placeHeatmap?.storage || {} },
  { key: 'auxiliary', name: '公辅场所（变配电站 / 空压 / 消防泵房）', stat: overview.placeHeatmap?.auxiliary || {} }
])

function resolveUrl(u) {
  return resolveBackendAssetUrl(u)
}

function go(path) {
  router.push(path)
}

function fetchOverview() {
  loading.value = true
  getCommandOverview()
    .then(res => {
      if (res && res.data) {
        Object.assign(overview, res.data)
      }
    })
    .finally(() => {
      loading.value = false
    })
}

onMounted(() => {
  fetchOverview()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mr8 { margin-right: 8px; }
.cockpit-banner {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  padding: 18px 22px;
  margin-bottom: 16px;
  border-radius: 8px;
  background: linear-gradient(120deg, #0b1f3a 0%, #154572 100%);
  color: #fff;
}
.cockpit-title { font-size: 20px; font-weight: 700; letter-spacing: 0.4px; }
.cockpit-sub { font-size: 13px; color: rgba(255, 255, 255, 0.82); margin-top: 4px; }
.cockpit-status { display: flex; flex-wrap: wrap; align-items: center; gap: 6px; }
.kpi-card { cursor: pointer; }
.kpi-label { font-size: 13px; color: #606266; }
.kpi-value { font-size: 26px; font-weight: 700; margin: 8px 0; }
.kpi-unit { font-size: 13px; font-weight: 400; }
.kpi-foot { font-size: 12px; color: #909399; }
.text-danger { color: #f56c6c; }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
.text-primary { color: #409eff; }
.section-hdr { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.sub-note { font-size: 12px; font-weight: 400; color: #909399; }
.plant-map-wrap { width: 100%; background: #fafbfc; border-radius: 6px; overflow: hidden; }
.plant-svg { width: 100%; height: auto; display: block; }
.hz-node { cursor: pointer; }
.hz-node:hover circle { opacity: 0.85; }
.place-heat-item { padding: 14px; margin-bottom: 12px; border-radius: 6px; border: 1px solid #ebeef5; background: #fcfcfd; }
.place-heat-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.place-heat-metrics { display: flex; justify-content: space-between; font-size: 13px; color: #606266; }
</style>
