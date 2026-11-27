<template>
  <div class="app-container">
    <!-- 动态风险画像联动预警横幅 -->
    <el-alert
      v-if="riskBanner.reEvalTriggered"
      type="warning"
      show-icon
      :closable="false"
      class="mb14"
      :title="riskBanner.warningMessage"
    />

    <!-- 评价场所、作业区与一键生成评价报告 -->
    <el-card shadow="never" class="mb16">
      <template #header>
        <div class="card-header">
          <span class="card-title">AI 动态安全评价引擎（确定性物理数学公式 + 隐患联动 + 智能报告）</span>
          <div>
            <el-button type="primary" size="small" icon="Document" :loading="generatingReport" @click="handleGenerateReport">
              一键生成 AI 专业安全评价报告
            </el-button>
          </div>
        </div>
      </template>

      <el-form :inline="true" label-width="95px">
        <el-form-item label="评价场所">
          <el-radio-group v-model="placeType" @change="handlePlaceChange">
            <el-radio-button label="production">生产场所评价</el-radio-button>
            <el-radio-button label="storage">储存场所评价</el-radio-button>
            <el-radio-button label="auxiliary">公辅场所评价</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="评价作业区">
          <el-select v-model="selectedDeptId" style="width: 210px" @change="onDeptChange">
            <el-option v-for="d in filteredDepts" :key="d.deptId" :label="d.deptName" :value="d.deptId" />
          </el-select>
        </el-form-item>
        <el-form-item label="评价工程师">
          <el-input v-model="evaluator" style="width: 140px" clearable />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 四大确定性算法工作区 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 1. 道氏火灾爆炸指数法 -->
      <el-tab-pane label="道氏指数法（Dow F&EI）" name="dow">
        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form :model="dowForm" label-width="180px">
              <el-form-item label="危险物质预设">
                <el-select v-model="dowPreset" style="width: 100%" @change="applyDowPreset">
                  <el-option v-for="item in dowPresets" :key="item.name" :label="`${item.name}（MF=${item.mf}）`" :value="item.name" />
                </el-select>
              </el-form-item>
              <el-form-item label="工艺单元名称">
                <el-input v-model="dowForm.unitName" />
              </el-form-item>
              <el-form-item label="物质系数（MF）">
                <el-input-number v-model="dowForm.mf" :min="1" :max="40" :step="1" style="width: 100%" />
              </el-form-item>
              <el-form-item label="一般工艺危险系数（F1）">
                <el-input-number v-model="dowForm.f1" :min="1" :max="10" :step="0.1" :precision="2" style="width: 100%" />
              </el-form-item>
              <el-form-item label="特殊工艺危险系数（F2）">
                <el-input-number v-model="dowForm.f2" :min="1" :max="10" :step="0.1" :precision="2" style="width: 100%" />
              </el-form-item>
              <el-form-item label="安全措施补偿系数（C）">
                <el-input-number v-model="dowForm.cFactor" :min="0.1" :max="1" :step="0.02" :precision="2" style="width: 100%" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" icon="Cpu" @click="calcDow">精确计算</el-button>
                <el-button type="warning" plain icon="MagicStick" @click="askAiAssist('DOW')">AI 参数依据建议</el-button>
                <el-button type="success" plain @click="archiveSingle('DOW', dowForm, dowResult, dowResult.compLevel)">归档</el-button>
              </el-form-item>
            </el-form>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-descriptions title="Dow F&EI 确定性计算结果" :column="1" border>
              <el-descriptions-item label="单元危险系数 F3 = F1 × F2"><strong>{{ dowResult.f3 }}</strong></el-descriptions-item>
              <el-descriptions-item label="初始火灾爆炸指数 F&EI = MF × F3"><strong>{{ dowResult.fei }}</strong></el-descriptions-item>
              <el-descriptions-item label="补偿后指数 F&EI' = F&EI × C"><strong>{{ dowResult.compensatedFei }}</strong></el-descriptions-item>
              <el-descriptions-item label="暴露区域半径 R / 面积 S">{{ dowResult.radius }} m / {{ dowResult.area }} m²</el-descriptions-item>
              <el-descriptions-item label="初始危险等级"><el-tag :type="dowResult.tagType">{{ dowResult.level }}</el-tag></el-descriptions-item>
              <el-descriptions-item label="补偿后危险等级"><el-tag :type="dowResult.compTagType">{{ dowResult.compLevel }}</el-tag></el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 2. 作业条件危险性分析法 LEC -->
      <el-tab-pane label="作业条件危险性分析法（LEC）" name="lec">
        <el-row :gutter="20">
          <el-col :xs="24" :md="12">
            <el-form :model="lecForm" label-width="220px">
              <el-form-item label="作业活动名称">
                <el-input v-model="lecForm.jobName" />
              </el-form-item>
              <el-form-item label="事故发生可能性（L）">
                <el-select v-model="lecForm.l" style="width: 100%">
                  <el-option v-for="i in lecOptionsL" :key="i.value" :label="`${i.value} - ${i.label}`" :value="i.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="暴露频繁程度（E）">
                <el-select v-model="lecForm.e" style="width: 100%">
                  <el-option v-for="i in lecOptionsE" :key="i.value" :label="`${i.value} - ${i.label}`" :value="i.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="事故可能后果（C）">
                <el-select v-model="lecForm.c" style="width: 100%">
                  <el-option v-for="i in lecOptionsC" :key="i.value" :label="`${i.value} - ${i.label}`" :value="i.value" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" icon="Cpu" @click="calcLec">计算分值 D</el-button>
                <el-button type="warning" plain icon="MagicStick" @click="askAiAssist('LEC')">AI 结合隐患动态推荐</el-button>
                <el-button type="success" plain @click="archiveSingle('LEC', lecForm, lecResult, lecResult.grade)">归档</el-button>
              </el-form-item>
            </el-form>
          </el-col>
          <el-col :xs="24" :md="12">
            <el-descriptions title="LEC 风险等级判定结果" :column="1" border>
              <el-descriptions-item label="当前取值">L={{ lecForm.l }}，E={{ lecForm.e }}，C={{ lecForm.c }}</el-descriptions-item>
              <el-descriptions-item label="危险性分值 D = L × E × C">
                <strong style="font-size: 18px">{{ lecResult.d }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="风险等级">
                <el-tag :type="lecResult.tagType">{{ lecResult.grade }}（{{ lecResult.levelText }}）</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="管控措施">{{ lecResult.advice }}</el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 3. TNT 当量法与厂区平面同心圆可视化 -->
      <el-tab-pane label="事故后果模拟法（TNT 平面同心圆波及图）" name="consequence">
        <el-row :gutter="20">
          <el-col :xs="24" :lg="10">
            <el-form :model="simForm" label-width="195px" size="default">
              <el-form-item label="关联重大危险源">
                <el-select v-model="simForm.hazardId" style="width: 100%" @change="onHazardSelect">
                  <el-option
                    v-for="h in hazardProfiles"
                    :key="h.hazardId"
                    :label="`${h.hazardName} (${h.chemicalName})`"
                    :value="h.hazardId"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="泄漏介质质量 Wf (kg)">
                <el-input-number v-model="simForm.wf" :min="10" :max="1000000" :step="200" style="width: 100%" />
              </el-form-item>
              <el-form-item label="蒸气云当量系数 α">
                <el-input-number v-model="simForm.alpha" :min="0.01" :max="0.2" :step="0.01" :precision="2" style="width: 100%" />
              </el-form-item>
              <el-form-item label="介质燃烧热 Qf (kJ/kg)">
                <el-input-number v-model="simForm.qf" :min="1000" :max="200000" :step="500" style="width: 100%" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" icon="Aim" @click="calcSimAndImpact">计算并叠加平面波及圈</el-button>
                <el-button type="success" plain @click="archiveSingle('TNT', simForm, simResult, `R1=${simResult.r1}m`)">归档</el-button>
              </el-form-item>
            </el-form>

            <el-descriptions :column="2" border size="small" class="mt8">
              <el-descriptions-item label="TNT当量">{{ simResult.wtnt }} kg</el-descriptions-item>
              <el-descriptions-item label="波及在岗人员">
                <b style="color: #f56c6c">{{ spatialImpact.affectedStaffInR3 || 0 }} 人</b>
              </el-descriptions-item>
              <el-descriptions-item label="死亡半径 R1"><el-tag size="small" type="danger">{{ simResult.r1 }} m</el-tag></el-descriptions-item>
              <el-descriptions-item label="重伤半径 R2"><el-tag size="small" type="warning">{{ simResult.r2 }} m</el-tag></el-descriptions-item>
              <el-descriptions-item label="轻伤半径 R3"><el-tag size="small" type="info">{{ simResult.r3 }} m</el-tag></el-descriptions-item>
              <el-descriptions-item label="财产损失 R4">{{ simResult.r4 }} m</el-descriptions-item>
              <el-descriptions-item label="受波及设备" :span="2">
                {{ (spatialImpact.affectedEquips || []).map(e => e.postName).join('、') || '周边管廊设施' }}
              </el-descriptions-item>
            </el-descriptions>
          </el-col>

          <el-col :xs="24" :lg="14">
            <div class="map-box">
              <div class="map-legend">
                <span>厂区电子平面比例尺：300m × 220m</span>
                <span>
                  <i class="dot r1"></i>R1死亡
                  <i class="dot r2"></i>R2重伤
                  <i class="dot r3"></i>R3轻伤警戒
                  <i class="dot r4"></i>R4财产损失
                </span>
              </div>
              <svg viewBox="0 0 600 440" class="tnt-svg">
                <rect x="10" y="10" width="280" height="420" rx="6" fill="#f8f9fb" stroke="#dcdfe6" />
                <text x="20" y="30" fill="#606266" font-size="12">生产场所区</text>
                <rect x="300" y="10" width="290" height="205" rx="6" fill="#fcfaf5" stroke="#dcdfe6" />
                <text x="312" y="30" fill="#606266" font-size="12">储存场所区</text>
                <rect x="300" y="225" width="290" height="205" rx="6" fill="#f4f8ff" stroke="#dcdfe6" />
                <text x="312" y="245" fill="#606266" font-size="12">公辅场所区</text>

                <!-- 同心圆叠加 (1m = 2px) -->
                <g v-if="centerCoords">
                  <circle :cx="centerCoords.cx" :cy="centerCoords.cy" :r="Number(simResult.r4) * 2" fill="rgba(64,158,255,0.10)" stroke="#409eff" stroke-dasharray="4,3" />
                  <circle :cx="centerCoords.cx" :cy="centerCoords.cy" :r="Number(simResult.r3) * 2" fill="rgba(230,162,60,0.16)" stroke="#e6a23c" stroke-width="1.5" />
                  <circle :cx="centerCoords.cx" :cy="centerCoords.cy" :r="Number(simResult.r2) * 2" fill="rgba(245,108,108,0.22)" stroke="#f56c6c" stroke-width="1.5" />
                  <circle :cx="centerCoords.cx" :cy="centerCoords.cy" :r="Number(simResult.r1) * 2" fill="rgba(217,0,27,0.38)" stroke="#b71c1c" stroke-width="2" />
                </g>

                <!-- 全部危险源点位标注 -->
                <g v-for="nd in spatialImpact.spatialNodes" :key="nd.hazardId">
                  <circle :cx="nd.mapX * 6" :cy="nd.mapY * 4.4" r="6" :fill="nd.hazardId === simForm.hazardId ? '#b71c1c' : '#303133'" />
                  <text :x="nd.mapX * 6 + 9" :y="nd.mapY * 4.4 + 4" font-size="11" fill="#1f2d3d">
                    {{ nd.hazardName }} ({{ nd.onDutyCount }}人 · {{ nd.impactZone }})
                  </text>
                </g>
              </svg>
            </div>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 4. 安全检查表法 SCL（含 RAG 国标条款自动推荐） -->
      <el-tab-pane label="安全检查表法（SCL + 国标推荐）" name="scl">
        <div class="scl-toolbar mb12">
          <div>
            <el-button type="primary" size="small" icon="MagicStick" @click="recommendSclFromRag">
              RAG 检索并追加当前场所最新国标检查项
            </el-button>
            <el-button type="success" size="small" plain icon="Plus" @click="addDialogVisible = true">手动新增项</el-button>
            <el-button type="warning" size="small" plain icon="Download" @click="exportChecklistCsv">导出 CSV</el-button>
          </div>
          <div>
            <el-tag type="info" class="mr8">总项数：{{ sclStats.total }}</el-tag>
            <el-tag type="success" class="mr8">符合：{{ sclStats.pass }}</el-tag>
            <el-tag type="danger" class="mr8">不符合：{{ sclStats.fail }}</el-tag>
            <el-tag :type="sclStats.rate >= 80 ? 'success' : 'warning'">合规率：{{ sclStats.rate }}%</el-tag>
          </div>
        </div>

        <el-table :data="tableData" border size="small">
          <el-table-column type="index" label="序号" width="60" align="center" />
          <el-table-column prop="name" label="检查项目与标准要求" min-width="320" />
          <el-table-column prop="standard" label="法规/国标出处" width="220" align="center" />
          <el-table-column label="检查结果" width="130" align="center">
            <template #default="{ row }">
              <el-select v-model="row.result" size="small">
                <el-option label="符合" value="符合" />
                <el-option label="不符合" value="不符合" />
                <el-option label="不适用" value="不适用" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="备注" min-width="180">
            <template #default="{ row }">
              <el-input v-model="row.remark" size="small" clearable />
            </template>
          </el-table-column>
          <el-table-column label="操作" width="70" align="center">
            <template #default="scope">
              <el-button link type="danger" size="small" @click="tableData.splice(scope.$index, 1)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- AI 参数建议审核弹窗 -->
    <el-dialog v-model="assistDialog.open" title="AI 智能评价参数推荐（需评价工程师复核确认）" width="560px" append-to-body>
      <el-alert type="info" :closable="false" title="严格遵循工程约束：大模型仅提供参数取值依据建议，最终公式计算由确定性程序执行。" class="mb12" />
      <div v-for="(r, idx) in assistDialog.rationales" :key="idx" class="rationale-line">
        {{ idx + 1 }}. {{ r }}
      </div>
      <el-descriptions :column="2" border size="small" class="mt12">
        <el-descriptions-item v-for="(val, k) in assistDialog.params" :key="k" :label="k">
          <strong>{{ val }}</strong>
        </el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button @click="assistDialog.open = false">取 消</el-button>
        <el-button type="primary" @click="applyAssistParams">审核通过并填入计算器</el-button>
      </template>
    </el-dialog>

    <!-- AI 安全评价报告预览与导出弹窗 -->
    <el-dialog v-model="reportDialog.open" title="AI 结构化安全评价报告预览与导出" width="760px" append-to-body>
      <pre class="report-pre">{{ reportDialog.markdown }}</pre>
      <template #footer>
        <el-button @click="exportReportFile('md')">导出 Markdown (.md)</el-button>
        <el-button type="primary" icon="Download" @click="exportReportFile('doc')">导出 Word 报告 (.doc)</el-button>
      </template>
    </el-dialog>

    <!-- 新增 SCL 项弹窗 -->
    <el-dialog v-model="addDialogVisible" title="新增安全检查项" width="500px" append-to-body>
      <el-form :model="newItem" label-width="95px">
        <el-form-item label="检查内容"><el-input v-model="newItem.name" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="标准依据"><el-input v-model="newItem.standard" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAddItem">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="Evaluate">
import { ElMessage } from 'element-plus'
import { listDept } from '@/api/system/dept'
import {
  getDynamicRiskStatus,
  saveEvalCalc,
  requestAiEvalAssist,
  generateAiEvalReport,
  queryTntSpatialImpact,
  listHazardProfiles,
  recommendKbLaws
} from '@/api/ehs'

const placeType = ref('production')
const activeTab = ref('dow')
const evaluator = ref('注册安全工程师')
const generatingReport = ref(false)

const allDepts = ref([])
const selectedDeptId = ref(103)
const hazardProfiles = ref([])

const riskBanner = reactive({
  reEvalTriggered: false,
  warningMessage: ''
})

const filteredDepts = computed(() => {
  if (!allDepts.value.length) {
    return [
      { deptId: 103, deptName: '采油作业区' },
      { deptId: 108, deptName: '甲醇储罐区' },
      { deptId: 111, deptName: '中心变配电与空压站' }
    ]
  }
  return allDepts.value.filter(d => d.parentId && Number(d.parentId) >= 100)
})

const currentAreaName = computed(() => {
  const found = filteredDepts.value.find(d => d.deptId === selectedDeptId.value)
  return found ? found.deptName : '采油作业区'
})

// ==================== 1. Dow F&EI ====================
const dowPresets = [
  { name: '甲醇（Methanol）', mf: 16 },
  { name: '一氧化碳（CO）', mf: 14 },
  { name: '甲烷 / 天然气（CH4）', mf: 21 },
  { name: '氢气（H2）', mf: 21 }
]
const dowPreset = ref(dowPresets[0].name)
const dowForm = reactive({ unitName: '甲醇精馏反应单元', mf: 16, f1: 2.0, f2: 1.9, cFactor: 0.72 })
const dowResult = reactive({ f3: '3.80', fei: '60.80', compensatedFei: '43.78', radius: '15.56', area: '761.08', level: '较轻', tagType: 'info', compLevel: '最轻', compTagType: 'success' })

function evalDowGrade(v) {
  if (v <= 60) return { level: '最轻（1~60）', tagType: 'success' }
  if (v <= 96) return { level: '较轻（61~96）', tagType: 'info' }
  if (v <= 127) return { level: '中等（97~127）', tagType: 'warning' }
  if (v <= 158) return { level: '很大（128~158）', tagType: 'danger' }
  return { level: '非常大（>158）', tagType: 'danger' }
}

function applyDowPreset(name) {
  const f = dowPresets.find(p => p.name === name)
  if (f) { dowForm.mf = f.mf; calcDow() }
}

function calcDow() {
  const f3 = Math.min(Number(dowForm.f1) * Number(dowForm.f2), 8.0)
  const fei = Number(dowForm.mf) * f3
  const compFei = fei * Number(dowForm.cFactor)
  const r = 0.256 * fei
  const s = Math.PI * r * r
  const g1 = evalDowGrade(fei)
  const g2 = evalDowGrade(compFei)
  dowResult.f3 = f3.toFixed(2)
  dowResult.fei = fei.toFixed(2)
  dowResult.compensatedFei = compFei.toFixed(2)
  dowResult.radius = r.toFixed(2)
  dowResult.area = s.toFixed(2)
  dowResult.level = g1.level; dowResult.tagType = g1.tagType
  dowResult.compLevel = g2.level; dowResult.compTagType = g2.tagType
}

// ==================== 2. LEC ====================
const lecOptionsL = [
  { value: 10, label: '完全可以预料' }, { value: 6, label: '相当可能' }, { value: 3, label: '可能，但不经常' },
  { value: 1, label: '可能性小，完全意外' }, { value: 0.5, label: '很不可能' }, { value: 0.2, label: '极不可能' }
]
const lecOptionsE = [
  { value: 10, label: '连续暴露' }, { value: 6, label: '每天工作时间内暴露' },
  { value: 3, label: '每周一次暴露' }, { value: 2, label: '每月一次暴露' }, { value: 1, label: '每年几次暴露' }
]
const lecOptionsC = [
  { value: 100, label: '10人以上死亡' }, { value: 40, label: '3~9人死亡' }, { value: 15, label: '1~2人死亡' },
  { value: 7, label: '严重伤残' }, { value: 3, label: '重大伤残' }, { value: 1, label: '轻伤' }
]
const lecForm = reactive({ jobName: '生产装置动火与受限空间巡检作业', l: 3, e: 6, c: 7 })
const lecResult = reactive({ d: '126.00', grade: '3级风险', levelText: '显著危险，需要整改', tagType: 'warning', advice: '' })

function calcLec() {
  const d = Number(lecForm.l) * Number(lecForm.e) * Number(lecForm.c)
  lecResult.d = d.toFixed(2)
  if (d > 320) {
    Object.assign(lecResult, { grade: '1级风险（极其危险）', levelText: '立即停止作业', tagType: 'danger', advice: '必须立即停产整顿，彻底消除重大隐患后方可恢复。' })
  } else if (d >= 160) {
    Object.assign(lecResult, { grade: '2级风险（高度危险）', levelText: '需立即整改', tagType: 'danger', advice: '立即采取工程联锁与专项防护措施降低风险。' })
  } else if (d >= 70) {
    Object.assign(lecResult, { grade: '3级风险（显著危险）', levelText: '限期整改', tagType: 'warning', advice: '严格落实特殊作业许可票证与专人现场监护。' })
  } else if (d >= 20) {
    Object.assign(lecResult, { grade: '4级风险（一般危险）', levelText: '需要注意', tagType: 'info', advice: '加强日常岗位规程抽查与个体防护穿戴检查。' })
  } else {
    Object.assign(lecResult, { grade: '5级风险（稍有危险）', levelText: '风险可接受', tagType: 'success', advice: '维持常态化安全巡检。' })
  }
}

// ==================== 3. TNT 平面同心圆模拟 ====================
const simForm = reactive({ hazardId: 2, wf: 5000, alpha: 0.04, qf: 19930, qtnt: 4520 })
const simResult = reactive({ wtnt: '0.00', r1: '0.00', r2: '0.00', r3: '0.00', r4: '0.00' })
const spatialImpact = reactive({ affectedStaffInR3: 0, affectedEquips: [], spatialNodes: [], centerHazard: null })

const centerCoords = computed(() => {
  const c = spatialImpact.centerHazard
  if (!c) return { cx: 432, cy: 140 }
  return { cx: Number(c.mapX) * 6, cy: Number(c.mapY) * 4.4 }
})

function onHazardSelect(hzId) {
  const hz = hazardProfiles.value.find(h => h.hazardId === hzId)
  if (hz && Number(hz.combustionHeatKj) > 0) {
    simForm.qf = Number(hz.combustionHeatKj)
  }
  calcSimAndImpact()
}

function calcSimAndImpact() {
  const wtnt = (Number(simForm.alpha) * Number(simForm.wf) * Number(simForm.qf)) / Number(simForm.qtnt)
  const cbrt = Math.cbrt(Math.max(wtnt, 0.001))
  const r1 = 13.6 * Math.pow(Math.max(wtnt, 0.001) / 1000, 0.37)
  const r2 = 3.4 * cbrt
  const r3 = 6.3 * cbrt
  const r4 = (4.6 * cbrt) / Math.pow(1 + Math.pow(3175 / Math.max(wtnt, 0.001), 2), 1 / 6)

  simResult.wtnt = wtnt.toFixed(2)
  simResult.r1 = r1.toFixed(2)
  simResult.r2 = r2.toFixed(2)
  simResult.r3 = r3.toFixed(2)
  simResult.r4 = r4.toFixed(2)

  queryTntSpatialImpact({
    hazardId: simForm.hazardId,
    r1: Number(simResult.r1),
    r2: Number(simResult.r2),
    r3: Number(simResult.r3),
    r4: Number(simResult.r4)
  }).then(res => {
    if (res && res.data) {
      Object.assign(spatialImpact, res.data)
    }
  }).catch(() => {})
}

// ==================== 4. SCL 安全检查表 ====================
const tableData = ref([
  { name: '生产、储存危险物品建设项目应当依法进行安全评价，配备专职安全生产管理人员。', standard: '《安全生产法》第32条', result: '符合', remark: '已配备注册安全工程师' },
  { name: '从业人员进入作业现场必须正确佩戴和使用符合国家标准的劳动防护用品（安全帽、防护服等）。', standard: '《安全生产法》第45条、第57条', result: '符合', remark: '视觉监控实时巡检' },
  { name: '动火、受限空间等特殊作业前必须开展气体分析并办理安全作业票，落实专人监护。', standard: 'GB 30871-2022', result: '符合', remark: '票证齐全' }
])

const sclStats = computed(() => {
  const list = tableData.value.filter(i => i.result !== '不适用')
  const pass = list.filter(i => i.result === '符合').length
  const fail = list.filter(i => i.result === '不符合').length
  const rate = list.length ? Math.round((pass / list.length) * 100) : 100
  return { total: tableData.value.length, pass, fail, rate }
})

function recommendSclFromRag() {
  const qMap = { production: '动火 受限空间 个体防护', storage: '危化品储存 重大危险源 防雷防静电', auxiliary: '安全设施 隐患排查' }
  recommendKbLaws({ query: qMap[placeType.value] || '安全生产', placeType: placeType.value, topK: 3 }).then(res => {
    const items = res.data || []
    let added = 0
    items.forEach(it => {
      const std = `${it.doc_title || it.docTitle} ${it.clause_no || it.clauseNo}`
      const txt = it.chunk_text || it.chunkText
      if (!tableData.value.some(r => r.standard === std)) {
        tableData.value.push({ name: txt, standard: std, result: '符合', remark: 'RAG知识库自动导入' })
        added++
      }
    })
    ElMessage.success(added > 0 ? `已从法规向量知识库导入 ${added} 条国标检查项` : '当前标准检查项已在列表中')
  })
}

const addDialogVisible = ref(false)
const newItem = reactive({ name: '', standard: '' })
function confirmAddItem() {
  if (!newItem.name.trim()) return
  tableData.value.push({ name: newItem.name.trim(), standard: newItem.standard.trim() || '企业安全制度', result: '符合', remark: '' })
  newItem.name = ''; newItem.standard = ''
  addDialogVisible.value = false
}

function exportChecklistCsv() {
  const headers = ['序号', '检查项目', '法规标准依据', '检查结果', '备注']
  const rows = tableData.value.map((r, i) => [i + 1, `"${r.name}"`, `"${r.standard}"`, r.result, `"${r.remark || ''}"`])
  const blob = new Blob(['\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `GliHub_${currentAreaName.value}_SCL检查表.csv`
  a.click()
}

// ==================== AI 参数辅助 & 归档 & 报告生成 ====================
const assistDialog = reactive({ open: false, method: 'LEC', params: {}, rationales: [] })

function askAiAssist(method) {
  requestAiEvalAssist({
    evalMethod: method,
    placeType: placeType.value,
    deptId: selectedDeptId.value,
    areaName: currentAreaName.value
  }).then(res => {
    if (res && res.data) {
      assistDialog.method = method
      assistDialog.params = res.data.recommended_params || {}
      assistDialog.rationales = res.data.rationale_items || []
      assistDialog.open = true
    }
  })
}

function applyAssistParams() {
  if (assistDialog.method === 'DOW') {
    Object.assign(dowForm, assistDialog.params)
    calcDow()
  } else {
    Object.assign(lecForm, assistDialog.params)
    calcLec()
  }
  assistDialog.open = false
  ElMessage.success('已应用建议参数并完成确定性公式重算')
}

function archiveSingle(method, inputObj, resultObj, grade) {
  saveEvalCalc({
    placeType: placeType.value,
    deptId: selectedDeptId.value,
    areaName: currentAreaName.value,
    evalMethod: method,
    inputParamsJson: JSON.stringify(inputObj),
    resultMetricsJson: JSON.stringify(resultObj),
    riskGrade: grade,
    evaluator: evaluator.value
  }).then(() => {
    ElMessage.success(`${method} 评价结果已归档入库`)
  })
}

const reportDialog = reactive({ open: false, markdown: '' })

function handleGenerateReport() {
  generatingReport.value = true
  generateAiEvalReport({
    placeType: placeType.value,
    deptId: selectedDeptId.value,
    areaName: currentAreaName.value,
    evaluator: evaluator.value,
    evalSummary: {
      dow: { ...dowForm, ...dowResult },
      lec: { ...lecForm, ...lecResult },
      tnt: { ...simForm, ...simResult },
      scl: sclStats.value
    }
  })
    .then(res => {
      reportDialog.markdown = res.data?.report_markdown || ''
      reportDialog.open = true
      ElMessage.success('AI 安全评价报告生成并自动归档成功')
    })
    .finally(() => {
      generatingReport.value = false
    })
}

function exportReportFile(ext) {
  const content = ext === 'doc'
    ? `<html><head><meta charset="utf-8"></head><body><pre style="font-family:SimSun,serif;white-space:pre-wrap;">${reportDialog.markdown}</pre></body></html>`
    : reportDialog.markdown
  const mime = ext === 'doc' ? 'application/msword;charset=utf-8' : 'text/markdown;charset=utf-8'
  const blob = new Blob([content], { type: mime })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `GliHub_${currentAreaName.value}_安全评价报告.${ext}`
  a.click()
}

function refreshDynamicRisk() {
  getDynamicRiskStatus({ deptId: selectedDeptId.value, placeType: placeType.value }).then(res => {
    if (res && res.data) Object.assign(riskBanner, res.data)
  }).catch(() => {})
}

function handlePlaceChange(val) {
  if (val === 'production') selectedDeptId.value = 103
  else if (val === 'storage') selectedDeptId.value = 108
  else selectedDeptId.value = 111
  refreshDynamicRisk()
}

function onDeptChange() {
  refreshDynamicRisk()
}

onMounted(() => {
  calcDow()
  calcLec()
  listDept().then(res => { allDepts.value = res.data || [] }).catch(() => {})
  listHazardProfiles().then(res => {
    hazardProfiles.value = res.data || []
    if (hazardProfiles.value.length) {
      simForm.hazardId = hazardProfiles.value[0].hazardId
      onHazardSelect(simForm.hazardId)
    } else {
      calcSimAndImpact()
    }
  }).catch(() => { calcSimAndImpact() })
  refreshDynamicRisk()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mb14 { margin-bottom: 14px; }
.mb12 { margin-bottom: 12px; }
.mt12 { margin-top: 12px; }
.mt8 { margin-top: 8px; }
.mr8 { margin-right: 8px; }
.card-header { display: flex; justify-content: space-between; align-items: center; }
.card-title { font-weight: 600; }
.scl-toolbar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 10px; }
.map-box { border: 1px solid #ebeef5; border-radius: 6px; padding: 10px; background: #fff; }
.map-legend { display: flex; justify-content: space-between; font-size: 12px; color: #606266; margin-bottom: 6px; }
.dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin: 0 4px 0 10px; }
.dot.r1 { background: #b71c1c; }
.dot.r2 { background: #f56c6c; }
.dot.r3 { background: #e6a23c; }
.dot.r4 { background: #409eff; }
.tnt-svg { width: 100%; height: auto; display: block; }
.rationale-line { font-size: 13px; line-height: 1.7; color: #303133; margin-bottom: 6px; }
.report-pre {
  max-height: 440px;
  overflow-y: auto;
  padding: 14px;
  background: #f8f9fb;
  border-radius: 6px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.65;
}
</style>
