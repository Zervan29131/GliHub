<template>
  <div class="app-container">
    <!-- 评价场所与作业区域选择 -->
    <el-card shadow="never" class="mb20">
      <template #header>
        <div class="card-header">
          <span class="card-title">安全评价单元配置（生产场所 / 储存场所 / 公辅场所）</span>
          <el-tag type="primary">{{ currentPlaceLabel }}</el-tag>
        </div>
      </template>
      <el-form :inline="true" label-width="100px">
        <el-form-item label="评价场所类别">
          <el-radio-group v-model="placeType" @change="handlePlaceChange">
            <el-radio-button label="production">生产场所评价</el-radio-button>
            <el-radio-button label="storage">储存场所评价</el-radio-button>
            <el-radio-button label="auxiliary">公辅场所评价</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="评价作业区域">
          <el-select v-model="selectedArea" placeholder="请选择评价作业区域" style="width: 220px">
            <el-option
              v-for="item in currentAreaOptions"
              :key="item"
              :label="item"
              :value="item"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="评价人员">
          <el-input v-model="evaluator" placeholder="安全评价工程师" clearable style="width: 160px" />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 四大安全评价方法计算程序 -->
    <el-tabs v-model="activeTab" type="border-card">
      <!-- 1. 道氏火灾、爆炸危险指数评价法 -->
      <el-tab-pane label="道氏指数法（Dow F&EI）" name="dow">
        <el-row :gutter="24">
          <el-col :xs="24" :md="13">
            <el-form :model="dowForm" label-width="190px">
              <el-form-item label="典型危险物质预设">
                <el-select v-model="dowPreset" placeholder="选择典型物质自动填入MF" style="width: 100%" @change="applyDowPreset">
                  <el-option v-for="item in dowPresets" :key="item.name" :label="`${item.name}（MF = ${item.mf}）`" :value="item.name" />
                </el-select>
              </el-form-item>
              <el-form-item label="评价工艺单元名称">
                <el-input v-model="dowForm.unitName" placeholder="例如：甲醇精馏单元" clearable />
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
                <el-button type="primary" icon="Cpu" @click="calcDow">计算道氏指数</el-button>
                <el-button icon="Refresh" @click="resetDow">重置</el-button>
              </el-form-item>
            </el-form>
          </el-col>
          <el-col :xs="24" :md="11">
            <el-descriptions title="道氏火灾爆炸指数计算结果" :column="1" border>
              <el-descriptions-item label="评价场所 / 区域">{{ currentPlaceLabel }} - {{ selectedArea }}</el-descriptions-item>
              <el-descriptions-item label="工艺单元">{{ dowForm.unitName || '-' }}</el-descriptions-item>
              <el-descriptions-item label="单元危险系数 F3 = F1 × F2">
                <strong>{{ dowResult.f3 }}</strong>
                <el-tag v-if="Number(dowResult.rawF3) > 8" type="warning" size="small" class="ml10">超出8.0按8.0计</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="初始火灾爆炸指数 F&EI = MF × F3">
                <strong>{{ dowResult.fei }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="补偿后火灾爆炸指数 F&EI' = F&EI × C">
                <strong>{{ dowResult.compensatedFei }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="暴露区域半径 R = 0.256 × F&EI">
                {{ dowResult.radius }} m
              </el-descriptions-item>
              <el-descriptions-item label="暴露区域面积 S = πR²">
                {{ dowResult.area }} m²
              </el-descriptions-item>
              <el-descriptions-item label="初始危险等级">
                <el-tag :type="dowResult.tagType">{{ dowResult.level }}</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="补偿后危险等级">
                <el-tag :type="dowResult.compTagType">{{ dowResult.compLevel }}</el-tag>
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 2. 作业条件危险性分析法（LEC） -->
      <el-tab-pane label="作业条件危险性分析法（LEC）" name="lec">
        <el-row :gutter="24">
          <el-col :xs="24" :md="13">
            <el-form :model="lecForm" label-width="230px">
              <el-form-item label="评价作业活动 / 岗位">
                <el-input v-model="lecForm.jobName" placeholder="例如：受限空间检修动火作业" clearable />
              </el-form-item>
              <el-form-item label="事故发生的可能性（L）">
                <el-select v-model="lecForm.l" style="width: 100%">
                  <el-option v-for="item in lecOptionsL" :key="item.value" :label="`${item.value} - ${item.label}`" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="人员暴露于危险环境频繁程度（E）">
                <el-select v-model="lecForm.e" style="width: 100%">
                  <el-option v-for="item in lecOptionsE" :key="item.value" :label="`${item.value} - ${item.label}`" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item label="发生事故可能造成的后果（C）">
                <el-select v-model="lecForm.c" style="width: 100%">
                  <el-option v-for="item in lecOptionsC" :key="item.value" :label="`${item.value} - ${item.label}`" :value="item.value" />
                </el-select>
              </el-form-item>
              <el-form-item>
                <el-button type="primary" icon="Cpu" @click="calcLec">计算危险性分值 D</el-button>
                <el-button icon="Refresh" @click="resetLec">重置</el-button>
              </el-form-item>
            </el-form>
          </el-col>
          <el-col :xs="24" :md="11">
            <el-descriptions title="LEC 作业条件危险性评定结果" :column="1" border>
              <el-descriptions-item label="评价场所 / 区域">{{ currentPlaceLabel }} - {{ selectedArea }}</el-descriptions-item>
              <el-descriptions-item label="作业活动">{{ lecForm.jobName || '-' }}</el-descriptions-item>
              <el-descriptions-item label="参数取值">L = {{ lecForm.l }}，E = {{ lecForm.e }}，C = {{ lecForm.c }}</el-descriptions-item>
              <el-descriptions-item label="危险性分值 D = L × E × C">
                <strong style="font-size: 18px">{{ lecResult.d }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="危险程度等级">
                <el-tag :type="lecResult.tagType">{{ lecResult.grade }}（{{ lecResult.levelText }}）</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="风险管控建议">{{ lecResult.advice }}</el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 3. 重大危险源事故后果模拟法（TNT当量法） -->
      <el-tab-pane label="事故后果模拟法（重大危险源爆炸冲击波）" name="consequence">
        <el-row :gutter="24">
          <el-col :xs="24" :md="13">
            <el-form :model="simForm" label-width="220px">
              <el-form-item label="重大危险源物质预设">
                <el-select v-model="simPreset" style="width: 100%" @change="applySimPreset">
                  <el-option
                    v-for="item in simPresets"
                    :key="item.name"
                    :label="`${item.name}（燃烧热 Qf = ${item.qf} kJ/kg）`"
                    :value="item.name"
                  />
                </el-select>
              </el-form-item>
              <el-form-item label="泄漏可燃介质总质量 Wf (kg)">
                <el-input-number v-model="simForm.wf" :min="1" :max="1000000" :step="100" style="width: 100%" />
              </el-form-item>
              <el-form-item label="蒸气云TNT当量系数 α">
                <el-input-number v-model="simForm.alpha" :min="0.01" :max="0.2" :step="0.01" :precision="2" style="width: 100%" />
              </el-form-item>
              <el-form-item label="可燃介质燃烧热 Qf (kJ/kg)">
                <el-input-number v-model="simForm.qf" :min="1000" :max="200000" :step="500" style="width: 100%" />
              </el-form-item>
              <el-form-item label="TNT爆炸热 QTNT (kJ/kg)">
                <el-input-number v-model="simForm.qtnt" :min="4000" :max="5000" :step="10" style="width: 100%" />
              </el-form-item>
              <el-form-item>
                <el-button type="primary" icon="Cpu" @click="calcSim">模拟事故后果</el-button>
                <el-button icon="Refresh" @click="resetSim">重置</el-button>
              </el-form-item>
            </el-form>
          </el-col>
          <el-col :xs="24" :md="11">
            <el-descriptions title="蒸气云爆炸冲击波伤害半径模拟结果" :column="1" border>
              <el-descriptions-item label="模拟区域 / 介质">{{ selectedArea }} - {{ simPreset }}</el-descriptions-item>
              <el-descriptions-item label="TNT当量 WTNT (kg)">
                <strong>{{ simResult.wtnt }} kg</strong>
              </el-descriptions-item>
              <el-descriptions-item label="死亡半径 R1">
                <el-tag type="danger">{{ simResult.r1 }} m</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="重伤半径 R2（ΔP ≥ 0.044 MPa）">
                <el-tag type="warning">{{ simResult.r2 }} m</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="轻伤半径 R3（ΔP ≥ 0.017 MPa）">
                <el-tag type="info">{{ simResult.r3 }} m</el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="财产损失半径 R4">
                <span>{{ simResult.r4 }} m</span>
              </el-descriptions-item>
              <el-descriptions-item label="应急疏散与防护建议">
                {{ simResult.advice }}
              </el-descriptions-item>
            </el-descriptions>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 4. 安全检查表法（SCL） -->
      <el-tab-pane label="安全检查表法（SCL）" name="scl">
        <div class="scl-toolbar mb15">
          <div>
            <el-button type="primary" icon="RefreshRight" @click="loadPlaceChecklist">
              加载「{{ currentPlaceLabel }}」标准检查项
            </el-button>
            <el-button type="success" plain icon="Plus" @click="openAddDialog">添加检查项目</el-button>
            <el-button type="warning" plain icon="Download" @click="exportChecklistCsv">导出检查表（CSV）</el-button>
          </div>
          <div class="scl-summary">
            <el-tag type="info" class="mr10">总项数：{{ sclStats.total }}</el-tag>
            <el-tag type="success" class="mr10">符合：{{ sclStats.pass }}</el-tag>
            <el-tag type="danger" class="mr10">不符合：{{ sclStats.fail }}</el-tag>
            <el-tag :type="sclStats.rate >= 80 ? 'success' : 'warning'">合格率：{{ sclStats.rate }}%</el-tag>
          </div>
        </div>

        <el-table :data="tableData" border style="width: 100%">
          <el-table-column type="index" label="序号" width="65" align="center" />
          <el-table-column prop="name" label="安全检查项目与技术要求" min-width="340" />
          <el-table-column prop="standard" label="国家法律与技术标准依据" width="230" align="center" />
          <el-table-column label="检查结果" width="140" align="center">
            <template #default="{ row }">
              <el-select v-model="row.result" size="small">
                <el-option label="符合" value="符合" />
                <el-option label="不符合" value="不符合" />
                <el-option label="不适用" value="不适用" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="现场整改备注" min-width="200">
            <template #default="{ row }">
              <el-input v-model="row.remark" size="small" placeholder="填写现场检查记录或整改措施" clearable />
            </template>
          </el-table-column>
          <el-table-column fixed="right" label="操作" width="80" align="center">
            <template #default="scope">
              <el-button link type="danger" size="small" @click="deleteRow(scope.$index)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加安全检查表项弹窗 -->
    <el-dialog v-model="addDialogVisible" title="添加安全检查项目" width="560px" append-to-body>
      <el-form :model="newItem" label-width="110px">
        <el-form-item label="检查项目内容">
          <el-input v-model="newItem.name" type="textarea" :rows="3" placeholder="请输入检查项目及要求" />
        </el-form-item>
        <el-form-item label="标准规范依据">
          <el-input v-model="newItem.standard" placeholder="例如：《安全生产法》第41条 / GB 18218" />
        </el-form-item>
        <el-form-item label="检查结果">
          <el-radio-group v-model="newItem.result">
            <el-radio label="符合">符合</el-radio>
            <el-radio label="不符合">不符合</el-radio>
            <el-radio label="不适用">不适用</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="newItem.remark" placeholder="选填整改说明" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="confirmAddItem">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="Evaluate">
import { ElMessage } from 'element-plus'
import { listDept } from '@/api/system/dept'

// ==================== 评价场所与作业区域 ====================
const placeType = ref('production')
const activeTab = ref('dow')
const evaluator = ref('安全评价组')

const placeLabels = {
  production: '生产场所评价',
  storage: '储存场所评价',
  auxiliary: '公辅场所评价'
}

const defaultPlaceAreas = {
  production: ['采油作业区', '油气矿仪陇作业区', '非煤山作业区', '智慧采矿区'],
  storage: ['甲醇储罐区', '危化品甲类仓库', '液化烃球罐区'],
  auxiliary: ['中心变配电站', '空压制氮站', '循环水与消防水泵房', '锅炉与公用工程区']
}

const deptAreaList = ref([])
const selectedArea = ref(defaultPlaceAreas.production[0])

const currentPlaceLabel = computed(() => placeLabels[placeType.value] || '生产场所评价')
const currentAreaOptions = computed(() => {
  const base = defaultPlaceAreas[placeType.value] || []
  if (placeType.value === 'production' && deptAreaList.value.length > 0) {
    return Array.from(new Set([...deptAreaList.value, ...base]))
  }
  return base
})

function loadDeptAreas() {
  listDept().then(res => {
    if (res && Array.isArray(res.data)) {
      const names = res.data
        .filter(d => d.parentId && Number(d.parentId) > 0 && d.deptName)
        .map(d => d.deptName)
      if (names.length > 0) {
        deptAreaList.value = names
        selectedArea.value = names[0]
      }
    }
  }).catch(() => {})
}

// ==================== 1. 道氏指数法（Dow F&EI） ====================
const dowPresets = [
  { name: '甲醇（Methanol）', mf: 16 },
  { name: '一氧化碳（CO）', mf: 14 },
  { name: '液化石油气 / 丙烷（LPG）', mf: 21 },
  { name: '甲烷 / 天然气（Methane）', mf: 21 },
  { name: '氢气（Hydrogen）', mf: 21 },
  { name: '甲苯（Toluene）', mf: 16 }
]
const dowPreset = ref(dowPresets[0].name)
const dowForm = reactive({
  unitName: '甲醇精馏反应单元',
  mf: 16,
  f1: 2.0,
  f2: 1.9,
  cFactor: 0.72
})

const dowResult = reactive({
  rawF3: '3.80',
  f3: '3.80',
  fei: '60.80',
  compensatedFei: '43.78',
  radius: '15.56',
  area: '761.08',
  level: '较轻',
  tagType: 'info',
  compLevel: '最轻',
  compTagType: 'success'
})

function evalDowGrade(feiVal) {
  if (feiVal <= 60) return { level: '最轻（1~60）', tagType: 'success' }
  if (feiVal <= 96) return { level: '较轻（61~96）', tagType: 'info' }
  if (feiVal <= 127) return { level: '中等（97~127）', tagType: 'warning' }
  if (feiVal <= 158) return { level: '很大（128~158）', tagType: 'danger' }
  return { level: '非常大（>158）', tagType: 'danger' }
}

function applyDowPreset(name) {
  const found = dowPresets.find(p => p.name === name)
  if (found) {
    dowForm.mf = found.mf
    calcDow()
  }
}

function calcDow() {
  const rawF3 = Number(dowForm.f1) * Number(dowForm.f2)
  const f3 = Math.min(rawF3, 8.0)
  const fei = Number(dowForm.mf) * f3
  const compFei = fei * Number(dowForm.cFactor)
  const radius = 0.256 * fei
  const area = Math.PI * radius * radius
  const initGrade = evalDowGrade(fei)
  const compGrade = evalDowGrade(compFei)

  dowResult.rawF3 = rawF3.toFixed(2)
  dowResult.f3 = f3.toFixed(2)
  dowResult.fei = fei.toFixed(2)
  dowResult.compensatedFei = compFei.toFixed(2)
  dowResult.radius = radius.toFixed(2)
  dowResult.area = area.toFixed(2)
  dowResult.level = initGrade.level
  dowResult.tagType = initGrade.tagType
  dowResult.compLevel = compGrade.level
  dowResult.compTagType = compGrade.tagType
}

function resetDow() {
  dowPreset.value = dowPresets[0].name
  dowForm.unitName = '甲醇精馏反应单元'
  dowForm.mf = 16
  dowForm.f1 = 2.0
  dowForm.f2 = 1.9
  dowForm.cFactor = 0.72
  calcDow()
}

// ==================== 2. 作业条件危险性分析法（LEC） ====================
const lecOptionsL = [
  { value: 10, label: '完全可以预料' },
  { value: 6, label: '相当可能' },
  { value: 3, label: '可能，但不经常' },
  { value: 1, label: '可能性小，完全意外' },
  { value: 0.5, label: '很不可能，可以设想' },
  { value: 0.2, label: '极不可能' },
  { value: 0.1, label: '实际不可能' }
]
const lecOptionsE = [
  { value: 10, label: '连续暴露' },
  { value: 6, label: '每天工作时间内暴露' },
  { value: 3, label: '每周一次或偶然暴露' },
  { value: 2, label: '每月一次暴露' },
  { value: 1, label: '每年几次暴露' },
  { value: 0.5, label: '非常罕见地暴露' }
]
const lecOptionsC = [
  { value: 100, label: '10人以上死亡（重大灾难）' },
  { value: 40, label: '3~9人死亡（灾难）' },
  { value: 15, label: '1~2人死亡（非常严重）' },
  { value: 7, label: '严重伤残（严重）' },
  { value: 3, label: '重大伤残或致残（重大）' },
  { value: 1, label: '轻伤，需救护（引人注目）' }
]

const lecForm = reactive({
  jobName: '生产装置动火与受限空间巡检作业',
  l: 3,
  e: 6,
  c: 7
})

const lecResult = reactive({
  d: '126.00',
  grade: '3级风险',
  levelText: '显著危险，需要整改',
  tagType: 'warning',
  advice: '应制定专项安全技术措施与作业票审批制度，限期落实整改并加强现场监护。'
})

function calcLec() {
  const d = Number(lecForm.l) * Number(lecForm.e) * Number(lecForm.c)
  lecResult.d = d.toFixed(2)
  if (d > 320) {
    lecResult.grade = '1级风险（极其危险）'
    lecResult.levelText = '不能继续作业'
    lecResult.tagType = 'danger'
    lecResult.advice = '必须立即停止作业，彻底消除重大事故隐患并经验收合格后方可恢复。'
  } else if (d >= 160) {
    lecResult.grade = '2级风险（高度危险）'
    lecResult.levelText = '需立即整改'
    lecResult.tagType = 'danger'
    lecResult.advice = '需立即采取工程技术与联锁防护措施降低风险，严格执行特种作业许可。'
  } else if (d >= 70) {
    lecResult.grade = '3级风险（显著危险）'
    lecResult.levelText = '需要整改'
    lecResult.tagType = 'warning'
    lecResult.advice = '应制定专项安全技术措施与作业票审批制度，限期落实整改并加强现场监护。'
  } else if (d >= 20) {
    lecResult.grade = '4级风险（一般危险）'
    lecResult.levelText = '需要注意'
    lecResult.tagType = 'info'
    lecResult.advice = '加强日常安全培训、个人防护用品佩戴检查与岗位操作规程抽查。'
  } else {
    lecResult.grade = '5级风险（稍有危险）'
    lecResult.levelText = '风险可接受'
    lecResult.tagType = 'success'
    lecResult.advice = '保持现有安全管控措施，做好常规班前巡检记录。'
  }
}

function resetLec() {
  lecForm.jobName = '生产装置动火与受限空间巡检作业'
  lecForm.l = 3
  lecForm.e = 6
  lecForm.c = 7
  calcLec()
}

// ==================== 3. 重大危险源事故后果模拟法（TNT当量法） ====================
const simPresets = [
  { name: '一氧化碳管道（CO）', qf: 10100, wf: 2000 },
  { name: '甲醇储罐（CH3OH）', qf: 19930, wf: 5000 },
  { name: '甲烷 / 天然气集输管线（CH4）', qf: 50040, wf: 1500 },
  { name: '液化石油气球罐（LPG）', qf: 46350, wf: 3000 },
  { name: '高压氢气汇流排（H2）', qf: 120900, wf: 500 }
]
const simPreset = ref(simPresets[1].name)
const simForm = reactive({
  wf: 5000,
  alpha: 0.04,
  qf: 19930,
  qtnt: 4520
})

const simResult = reactive({
  wtnt: '0.00',
  r1: '0.00',
  r2: '0.00',
  r3: '0.00',
  r4: '0.00',
  advice: ''
})

function applySimPreset(name) {
  const found = simPresets.find(p => p.name === name)
  if (found) {
    simForm.qf = found.qf
    simForm.wf = found.wf
    calcSim()
  }
}

function calcSim() {
  const wtnt = (Number(simForm.alpha) * Number(simForm.wf) * Number(simForm.qf)) / Number(simForm.qtnt)
  const cbrtW = Math.cbrt(Math.max(wtnt, 0.001))
  const r1 = 13.6 * Math.pow(Math.max(wtnt, 0.001) / 1000, 0.37)
  const r2 = 3.4 * cbrtW
  const r3 = 6.3 * cbrtW
  const r4 = (4.6 * cbrtW) / Math.pow(1 + Math.pow(3175 / Math.max(wtnt, 0.001), 2), 1 / 6)

  simResult.wtnt = wtnt.toFixed(2)
  simResult.r1 = r1.toFixed(2)
  simResult.r2 = r2.toFixed(2)
  simResult.r3 = r3.toFixed(2)
  simResult.r4 = r4.toFixed(2)
  simResult.advice = `建议以泄漏源为中心设立至少 ${Math.ceil(r3)} m 应急警戒疏散圈；${Math.ceil(r2)} m 范围内严禁非防爆设备及无关作业人员滞留，并配置固定式可燃/有毒气体声光报警联锁切断装置。`
}

function resetSim() {
  simPreset.value = simPresets[1].name
  simForm.wf = 5000
  simForm.alpha = 0.04
  simForm.qf = 19930
  simForm.qtnt = 4520
  calcSim()
}

// ==================== 4. 安全检查表法（SCL） ====================
const checklistTemplates = {
  production: [
    {
      name: '矿山、金属冶炼和用于生产、储存、装卸危险物品的建设项目，应当依法进行安全评价，设置安全生产管理机构或配备专职安全生产管理人员。',
      standard: '《安全生产法》第24条、第32条',
      result: '符合',
      remark: '已配备专职注册安全工程师'
    },
    {
      name: '生产经营单位应当对从业人员进行安全生产教育和培训；特种作业人员必须按照国家有关规定经专门的安全作业培训并取得相应资格，方可上岗作业。',
      standard: '《安全生产法》第28条、第30条',
      result: '符合',
      remark: '全员持证上岗台账齐全'
    },
    {
      name: '生产场所进行爆破、吊装、动火、临时用电及受限空间等危险作业，应当安排专门人员进行现场安全管理，确保操作规程遵守和安全措施落实。',
      standard: '《安全生产法》第43条 / GB 30871',
      result: '符合',
      remark: '严格执行八大特殊作业票证审批'
    },
    {
      name: '涉及一氧化碳、可燃气体生产工艺装置区应按规范设置可燃及有毒气体检测报警器，且报警信号应发送至24小时有人值守控制室。',
      standard: 'GB/T 50493《石油化工可燃气体和有毒气体检测报警设计标准》',
      result: '符合',
      remark: '探头定期检定合格'
    }
  ],
  storage: [
    {
      name: '危险化学品应当储存在专用仓库、专用场地或者专用储存室内，并由专人负责管理；剧毒化学品以及构成重大危险源的危险化学品必须在专用仓库内单独存放，实行双人收发、双人保管制度。',
      standard: '《危险化学品安全管理条例》第24条',
      result: '符合',
      remark: '实行双人双锁管理'
    },
    {
      name: '甲、乙类液体储罐区应设置防火堤，防火堤的有效容量不应小于其中最大储罐的容量，且管线穿堤处应采用非燃烧材料严密封闭。',
      standard: 'GB 50016《建筑设计防火规范》',
      result: '符合',
      remark: '防火堤完好无裂缝'
    },
    {
      name: '禁忌物料不得混存，灭火方法不同的危险化学品必须分间、分库储存，并在醒目处标明储存物品的名称、性质和灭火方法。',
      standard: 'GB 15603《危险化学品仓库储存通则》',
      result: '符合',
      remark: '设置MSDS安全周知卡'
    },
    {
      name: '重大危险源储罐区应当配备温度、压力、液位、流量等信息的不间断采集和监测系统以及紧急切断联锁装置。',
      standard: '《危险化学品重大危险源监督管理暂行规定》第13条',
      result: '符合',
      remark: 'SIS紧急切断联锁投用正常'
    }
  ],
  auxiliary: [
    {
      name: '变配电室门窗应向外开启，电缆沟及穿墙孔洞应采用防火泥严密封堵，室内配置足量二氧化碳或干粉灭火器及绝缘防护用具。',
      standard: 'GB 50053《20kV及以下变电所设计规范》',
      result: '符合',
      remark: '防小动物挡板及绝缘靴齐全'
    },
    {
      name: '压力容器、压力管道（空压储气罐、蒸汽分汽缸等）必须在检验有效期内使用，安全阀、压力表、爆破片等安全附件定期校验并挂牌标识。',
      standard: 'TSG 21《固定式压力容器安全技术监察规程》',
      result: '符合',
      remark: '年度定检合格'
    },
    {
      name: '消防水池水位、消防稳压泵及备用柴油机消防泵应处于自动/热备可用状态，厂区环形消防水幕与消火栓管网压力达标。',
      standard: 'GB 50974《消防给水及消火栓系统技术规范》',
      result: '符合',
      remark: '管网稳压 0.45 MPa'
    },
    {
      name: '公辅工程通风排烟、防雷防静电接地装置每年雷雨季节前定期检测，接地电阻值符合规范要求。',
      standard: 'GB 50057《建筑物防雷设计规范》',
      result: '符合',
      remark: '防雷检测报告合格'
    }
  ]
}

const tableData = ref(JSON.parse(JSON.stringify(checklistTemplates.production)))

const sclStats = computed(() => {
  const list = tableData.value
  const applicable = list.filter(i => i.result !== '不适用')
  const pass = applicable.filter(i => i.result === '符合').length
  const fail = applicable.filter(i => i.result === '不符合').length
  const rate = applicable.length > 0 ? Math.round((pass / applicable.length) * 100) : 100
  return { total: list.length, pass, fail, rate }
})

function handlePlaceChange(val) {
  const areas = defaultPlaceAreas[val] || []
  if (val === 'production' && deptAreaList.value.length > 0) {
    selectedArea.value = deptAreaList.value[0]
  } else if (areas.length > 0) {
    selectedArea.value = areas[0]
  }
  if (val === 'production') {
    dowForm.unitName = '甲醇精馏反应单元'
    lecForm.jobName = '生产装置动火与受限空间巡检作业'
  } else if (val === 'storage') {
    dowForm.unitName = '甲醇储罐区单元'
    lecForm.jobName = '危化品装卸栈台鹤管连接作业'
  } else {
    dowForm.unitName = '公用工程空压制氮与配电单元'
    lecForm.jobName = '高压配电柜倒闸与压力容器巡检'
  }
  tableData.value = JSON.parse(JSON.stringify(checklistTemplates[val] || checklistTemplates.production))
  calcDow()
  calcLec()
}

function loadPlaceChecklist() {
  tableData.value = JSON.parse(JSON.stringify(checklistTemplates[placeType.value] || checklistTemplates.production))
  ElMessage.success(`已加载「${currentPlaceLabel.value}」标准检查表`)
}

function deleteRow(index) {
  tableData.value.splice(index, 1)
}

const addDialogVisible = ref(false)
const newItem = reactive({
  name: '',
  standard: '',
  result: '符合',
  remark: ''
})

function openAddDialog() {
  newItem.name = ''
  newItem.standard = ''
  newItem.result = '符合'
  newItem.remark = ''
  addDialogVisible.value = true
}

function confirmAddItem() {
  if (!newItem.name.trim()) {
    ElMessage.warning('请输入检查项目内容')
    return
  }
  tableData.value.push({
    name: newItem.name.trim(),
    standard: newItem.standard.trim() || '企业安全生产管理制度',
    result: newItem.result,
    remark: newItem.remark.trim()
  })
  addDialogVisible.value = false
  ElMessage.success('检查项目添加成功')
}

function exportChecklistCsv() {
  const headers = ['序号', '评价场所', '评价区域', '检查项目', '国家法律与技术标准依据', '检查结果', '备注']
  const rows = tableData.value.map((row, idx) => [
    idx + 1,
    currentPlaceLabel.value,
    selectedArea.value,
    `"${(row.name || '').replace(/"/g, '""')}"`,
    `"${(row.standard || '').replace(/"/g, '""')}"`,
    row.result,
    `"${(row.remark || '').replace(/"/g, '""')}"`
  ])
  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = `GliHub_${currentPlaceLabel.value}_安全检查表.csv`
  link.click()
  URL.revokeObjectURL(link.href)
}

// 初始化默认计算结果
loadDeptAreas()
calcDow()
calcLec()
calcSim()
</script>

<style scoped>
.mb20 {
  margin-bottom: 20px;
}
.mb15 {
  margin-bottom: 15px;
}
.mr10 {
  margin-right: 10px;
}
.ml10 {
  margin-left: 10px;
}
.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.card-title {
  font-weight: 600;
  font-size: 15px;
}
.scl-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.scl-summary {
  display: flex;
  align-items: center;
}
</style>
