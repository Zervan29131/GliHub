<template>
  <div class="app-container">
    <el-form v-show="showSearch" ref="queryRef" :model="queryParams" :inline="true" label-width="76px">
      <el-form-item label="作业任务" prop="taskName">
        <el-input v-model="queryParams.taskName" placeholder="搜索作业任务或工序" clearable @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="风险类型" prop="riskCategory">
        <el-select v-model="queryParams.riskCategory" placeholder="全部要素" clearable style="width: 150px">
          <el-option label="人（违章/失误）" value="人" />
          <el-option label="机（设备/仪表）" value="机" />
          <el-option label="料（危化介质）" value="料" />
          <el-option label="环（作业环境）" value="环" />
          <el-option label="管（制度/监护）" value="管" />
        </el-select>
      </el-form-item>
      <el-form-item label="风险等级" prop="riskColor">
        <el-select v-model="queryParams.riskColor" placeholder="四色等级" clearable style="width: 150px">
          <el-option label="红色（重大风险）" value="红色" />
          <el-option label="橙色（较大风险）" value="橙色" />
          <el-option label="黄色（一般风险）" value="黄色" />
          <el-option label="蓝色（低风险）" value="蓝色" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Plus" @click="handleAdd">新增辨识项</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="warning" plain icon="Download" @click="handleExportCsv">导出 JHA 台账</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="handleQuery" />
    </el-row>

    <el-table :data="filteredRows" border style="width: 100%">
      <el-table-column type="index" align="center" label="序号" width="55" />
      <el-table-column prop="taskName" label="作业任务" min-width="145" />
      <el-table-column prop="stepName" label="作业步骤 / 工序" min-width="140" />
      <el-table-column prop="hazardSource" label="危险源或潜在事件" min-width="160" />
      <el-table-column prop="riskCategory" align="center" label="要素" width="65">
        <template #default="{ row }">
          <el-tag size="small" type="info">{{ row.riskCategory }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="consequence" label="可能导致的事故与后果" min-width="165" />
      <el-table-column prop="accidentType" align="center" label="事故类别" width="105" />
      <el-table-column align="center" label="风险矩阵评估 (R = L × S)">
        <el-table-column prop="likelihood" align="center" label="可能性 L" width="75" />
        <el-table-column prop="severity" align="center" label="严重度 S" width="75" />
        <el-table-column prop="riskScore" align="center" label="风险值 R" width="75" />
        <el-table-column prop="riskColor" align="center" label="四色分级" width="90">
          <template #default="{ row }">
            <el-tag size="small" :type="colorTagType(row.riskColor)" effect="dark">{{ row.riskColor }}</el-tag>
          </template>
        </el-table-column>
      </el-table-column>
      <el-table-column prop="controlMeasure" label="工程与管理管控标准" min-width="220" show-overflow-tooltip />
      <el-table-column prop="manager" align="center" label="责任人" width="85" />
      <el-table-column label="操作" align="center" width="135" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" size="small" icon="Edit" @click="handleUpdate(row)">修改</el-button>
          <el-button link type="danger" size="small" icon="Delete" @click="handleDelete(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <el-dialog v-model="open" :title="dialogTitle" width="620px" append-to-body>
      <el-form ref="formRef" :model="form" :rules="rules" label-width="110px">
        <el-row :gutter="12">
          <el-col :span="12">
            <el-form-item label="作业任务" prop="taskName">
              <el-input v-model="form.taskName" placeholder="如：甲醇储罐卸车作业" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="工序步骤" prop="stepName">
              <el-input v-model="form.stepName" placeholder="如：连接静电接地夹与鹤管" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="风险要素">
              <el-select v-model="form.riskCategory" style="width: 100%">
                <el-option label="人（违章/操作）" value="人" />
                <el-option label="机（设备/设施）" value="机" />
                <el-option label="料（危化物料）" value="料" />
                <el-option label="环（作业环境）" value="环" />
                <el-option label="管（管理缺陷）" value="管" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="事故类别">
              <el-input v-model="form.accidentType" placeholder="如：火灾爆炸 / 中毒窒息" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="危险源描述" prop="hazardSource">
              <el-input v-model="form.hazardSource" placeholder="如：静电跨接失效或未静置稳油" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="后果描述">
              <el-input v-model="form.consequence" placeholder="如：静电火花引燃可燃蒸气云引发燃爆" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="可能性 L">
              <el-input-number v-model="form.likelihood" :min="1" :max="5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="严重度 S">
              <el-input-number v-model="form.severity" :min="1" :max="5" style="width: 100%" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="责任人">
              <el-input v-model="form.manager" placeholder="如：安全员" />
            </el-form-item>
          </el-col>
          <el-col :span="24">
            <el-form-item label="管控措施" prop="controlMeasure">
              <el-input v-model="form.controlMeasure" type="textarea" :rows="3" placeholder="填写工程联锁、个体防护与现场监护措施" />
            </el-form-item>
          </el-col>
        </el-row>
      </el-form>
      <template #footer>
        <el-button @click="open = false">取 消</el-button>
        <el-button type="primary" @click="submitForm">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="Identify">
import { ElMessage, ElMessageBox } from 'element-plus'

const showSearch = ref(true)
const open = ref(false)
const dialogTitle = ref('新增工序风险辨识项')
const formRef = ref(null)

const queryParams = reactive({
  taskName: '',
  riskCategory: '',
  riskColor: ''
})

const allRows = ref([
  {
    id: 1,
    taskName: '甲醇储罐区装卸车作业',
    stepName: '连接鹤管与防静电接地夹',
    hazardSource: '静电接地报警器失效或未静置15分钟',
    riskCategory: '机',
    consequence: '静电放电引燃挥发甲醇蒸气云',
    accidentType: '火灾爆炸',
    likelihood: 3,
    severity: 5,
    riskScore: 15,
    riskColor: '橙色',
    controlMeasure: '必须采用声光联锁人体/槽车静电接地仪，装卸全程专人监护并开启可燃气体声光报警。',
    manager: '张安全'
  },
  {
    id: 2,
    taskName: '合成气管廊特级动火检修',
    stepName: '盲板抽堵与可燃气体采样分析',
    hazardSource: '阀门内漏或动火前30min未重新取样分析',
    riskCategory: '人',
    consequence: '一氧化碳/氢气泄漏遇动火火花爆炸中毒',
    accidentType: '中毒与爆炸',
    likelihood: 4,
    severity: 5,
    riskScore: 20,
    riskColor: '红色',
    controlMeasure: '严格执行 GB 30871 特级动火票证，加装盲板隔离，便携式复合气体检测仪连续监测。',
    manager: '李主任'
  },
  {
    id: 3,
    taskName: '中心变配电室高压柜清灰巡检',
    stepName: '停电验电挂接地线及除尘作业',
    hazardSource: '未穿戴绝缘靴/绝缘手套或误入带电间隔',
    riskCategory: '人',
    consequence: '高压电弧灼伤或触电伤亡',
    accidentType: '触电事故',
    likelihood: 2,
    severity: 4,
    riskScore: 8,
    riskColor: '黄色',
    controlMeasure: '严格执行停电、验电、装设接地线、悬挂标示牌和装设遮栏五步制度，双人监护。',
    manager: '王工'
  },
  {
    id: 4,
    taskName: '消防泵房稳压系统例行点检',
    stepName: '核查消火栓管网压力与备用柴油泵自启',
    hazardSource: '管网稳压阀门误关闭或蓄电池亏电',
    riskCategory: '管',
    consequence: '初期火灾消防水压不足延误扑救',
    accidentType: '火灾蔓延',
    likelihood: 2,
    severity: 2,
    riskScore: 4,
    riskColor: '蓝色',
    controlMeasure: '每周开展一次消防稳压泵手动/自动盘车测试并登记台账。',
    manager: '刘班长'
  }
])

const activeFilter = reactive({ taskName: '', riskCategory: '', riskColor: '' })

const filteredRows = computed(() => {
  return allRows.value.filter(r => {
    const kw = activeFilter.taskName.trim()
    if (kw && !(`${r.taskName}${r.stepName}${r.hazardSource}`.includes(kw))) return false
    if (activeFilter.riskCategory && r.riskCategory !== activeFilter.riskCategory) return false
    if (activeFilter.riskColor && r.riskColor !== activeFilter.riskColor) return false
    return true
  })
})

function computeColor(score) {
  if (score >= 16) return '红色'
  if (score >= 10) return '橙色'
  if (score >= 6) return '黄色'
  return '蓝色'
}

function colorTagType(color) {
  if (color === '红色') return 'danger'
  if (color === '橙色') return 'warning'
  if (color === '黄色') return 'primary'
  return 'info'
}

function handleQuery() {
  activeFilter.taskName = queryParams.taskName || ''
  activeFilter.riskCategory = queryParams.riskCategory || ''
  activeFilter.riskColor = queryParams.riskColor || ''
}

function resetQuery() {
  queryParams.taskName = ''
  queryParams.riskCategory = ''
  queryParams.riskColor = ''
  handleQuery()
}

const form = reactive({
  id: null,
  taskName: '',
  stepName: '',
  hazardSource: '',
  riskCategory: '人',
  consequence: '',
  accidentType: '其他伤害',
  likelihood: 2,
  severity: 3,
  controlMeasure: '',
  manager: '安全员'
})

const rules = {
  taskName: [{ required: true, message: '请输入作业任务名称', trigger: 'blur' }],
  stepName: [{ required: true, message: '请输入工序步骤', trigger: 'blur' }],
  hazardSource: [{ required: true, message: '请输入危险源描述', trigger: 'blur' }],
  controlMeasure: [{ required: true, message: '请输入管控措施', trigger: 'blur' }]
}

function handleAdd() {
  Object.assign(form, {
    id: null,
    taskName: '',
    stepName: '',
    hazardSource: '',
    riskCategory: '人',
    consequence: '',
    accidentType: '火灾爆炸',
    likelihood: 3,
    severity: 4,
    controlMeasure: '',
    manager: '安全员'
  })
  dialogTitle.value = '新增工序风险辨识项 (JHA)'
  open.value = true
}

function handleUpdate(row) {
  Object.assign(form, { ...row })
  dialogTitle.value = '修改工序风险辨识项'
  open.value = true
}

function submitForm() {
  formRef.value?.validate(valid => {
    if (!valid) return
    const score = Number(form.likelihood) * Number(form.severity)
    const record = {
      ...form,
      id: form.id || Date.now(),
      riskScore: score,
      riskColor: computeColor(score)
    }
    if (form.id) {
      const idx = allRows.value.findIndex(x => x.id === form.id)
      if (idx > -1) allRows.value.splice(idx, 1, record)
      ElMessage.success('工序风险辨识记录已更新')
    } else {
      allRows.value.unshift(record)
      ElMessage.success('工序风险辨识记录已新增')
    }
    open.value = false
  })
}

function handleDelete(row) {
  ElMessageBox.confirm(`确认删除「${row.taskName} - ${row.stepName}」风险辨识记录吗？`, '系统提示', { type: 'warning' })
    .then(() => {
      allRows.value = allRows.value.filter(x => x.id !== row.id)
      ElMessage.success('删除成功')
    })
    .catch(() => {})
}

function handleExportCsv() {
  const headers = ['序号', '作业任务', '工序步骤', '危险源', '要素', '后果描述', '事故类别', 'L', 'S', 'R', '四色等级', '管控措施', '责任人']
  const rows = filteredRows.value.map((r, i) => [
    i + 1,
    `"${r.taskName}"`,
    `"${r.stepName}"`,
    `"${r.hazardSource}"`,
    r.riskCategory,
    `"${r.consequence}"`,
    r.accidentType,
    r.likelihood,
    r.severity,
    r.riskScore,
    r.riskColor,
    `"${r.controlMeasure}"`,
    r.manager
  ])
  const blob = new Blob(['\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')], { type: 'text/csv;charset=utf-8;' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = 'GliHub_JHA工序风险辨识台账.csv'
  a.click()
  URL.revokeObjectURL(a.href)
}
</script>
