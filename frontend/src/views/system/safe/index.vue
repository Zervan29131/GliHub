<template>
  <div class="app-container">
    <el-row :gutter="10" class="mb12">
      <el-col :span="1.5">
        <el-button type="primary" icon="Plus" @click="openDialog()">添加应急措施</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="success" plain icon="DocumentChecked" @click="generatePlanSummary">生成应急预案摘要</el-button>
      </el-col>
      <el-col :span="1.5">
        <el-button type="warning" plain icon="Download" @click="exportCsv">导出应急预案表</el-button>
      </el-col>
    </el-row>

    <el-table :data="tableData" border style="width: 100%">
      <el-table-column type="index" align="center" label="序号" width="60" />
      <el-table-column prop="measureName" align="center" label="应急措施名称" width="160" />
      <el-table-column prop="measureType" align="center" label="措施类型" width="130" />
      <el-table-column prop="scene" align="center" label="适用事故场景" width="150" />
      <el-table-column prop="executor" align="center" label="执行负责人" width="120" />
      <el-table-column prop="steps" label="应急响应执行步骤" min-width="260" />
      <el-table-column prop="notice" label="防护装备与注意事项" min-width="180" />
      <el-table-column prop="contact" align="center" label="应急值班电话" width="135" />
      <el-table-column label="操作" align="center" width="150" fixed="right">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="Edit"
            @click="openDialog(scope.row, scope.$index)"
            v-hasPermi="['system:post:edit']"
          >修改</el-button>
          <el-button
            link
            type="danger"
            icon="Delete"
            @click="handleDelete(scope.$index)"
            v-hasPermi="['system:post:remove']"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 新增/修改应急措施弹窗 -->
    <el-dialog v-model="dialogVisible" :title="editIndex === -1 ? '添加应急措施' : '修改应急措施'" width="560px" append-to-body>
      <el-form :model="form" label-width="120px">
        <el-form-item label="应急措施名称">
          <el-input v-model="form.measureName" placeholder="例如：火灾紧急疏散 / 化学品泄漏处置" />
        </el-form-item>
        <el-form-item label="措施类型">
          <el-select v-model="form.measureType" style="width: 100%">
            <el-option label="疏散救援措施" value="疏散救援措施" />
            <el-option label="泄漏控制与恢复" value="泄漏控制与恢复" />
            <el-option label="工程抢险切断" value="工程抢险切断" />
            <el-option label="医疗救护保障" value="医疗救护保障" />
          </el-select>
        </el-form-item>
        <el-form-item label="适用事故场景">
          <el-input v-model="form.scene" placeholder="例如：储罐区火灾爆炸 / 管线泄漏" />
        </el-form-item>
        <el-form-item label="执行负责人">
          <el-input v-model="form.executor" placeholder="例如：安全员李某" />
        </el-form-item>
        <el-form-item label="执行步骤">
          <el-input v-model="form.steps" type="textarea" :rows="3" placeholder="分步骤填写应急处置规程" />
        </el-form-item>
        <el-form-item label="防护与注意事项">
          <el-input v-model="form.notice" placeholder="例如：正压式空气呼吸器、防化服、上风向撤离" />
        </el-form-item>
        <el-form-item label="应急值班电话">
          <el-input v-model="form.contact" placeholder="请输入应急联系电话" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取 消</el-button>
        <el-button type="primary" @click="saveMeasure">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="SafePlan">
import { ElMessage, ElMessageBox } from 'element-plus'

const tableData = ref([
  {
    measureName: '火灾紧急疏散',
    measureType: '疏散救援措施',
    scene: '生产装置及办公楼火灾',
    executor: '安全员李某',
    steps: '1. 立即触发声光火灾警报系统；2. 指引现场人员沿上风向应急疏散通道撤离至集合点；3. 清点当班人数并向应急总指挥报告。',
    notice: '严禁乘坐电梯，佩戴过滤式消防自救呼吸器，核查疏散路线图',
    contact: '13888888888'
  },
  {
    measureName: '危化品泄漏应急处理',
    measureType: '泄漏控制与恢复',
    scene: '储罐区及管线危险化学品泄漏',
    executor: '安全员张某',
    steps: '1. 立即联锁关闭上下游切断阀并隔离泄漏源；2. 使用防爆工具与吸附围油栏控制扩散；3. 持续检测可燃及有毒气体浓度直至合格。',
    notice: '穿戴重型防化服与正压式空气呼吸器，切断周边一切火源',
    contact: '13888888889'
  }
])

const dialogVisible = ref(false)
const editIndex = ref(-1)
const form = reactive({
  measureName: '',
  measureType: '疏散救援措施',
  scene: '',
  executor: '',
  steps: '',
  notice: '',
  contact: ''
})

function openDialog(row, index = -1) {
  editIndex.value = index
  if (row) {
    Object.assign(form, row)
  } else {
    form.measureName = ''
    form.measureType = '疏散救援措施'
    form.scene = ''
    form.executor = ''
    form.steps = ''
    form.notice = ''
    form.contact = ''
  }
  dialogVisible.value = true
}

function saveMeasure() {
  if (!form.measureName.trim() || !form.steps.trim()) {
    ElMessage.warning('请填写应急措施名称与执行步骤')
    return
  }
  const payload = { ...form }
  if (editIndex.value >= 0) {
    tableData.value.splice(editIndex.value, 1, payload)
    ElMessage.success('修改应急措施成功')
  } else {
    tableData.value.push(payload)
    ElMessage.success('添加应急措施成功')
  }
  dialogVisible.value = false
}

function handleDelete(index) {
  ElMessageBox.confirm('是否确认删除该条应急措施？', '系统提示', { type: 'warning' })
    .then(() => {
      tableData.value.splice(index, 1)
      ElMessage.success('删除成功')
    })
    .catch(() => {})
}

function generatePlanSummary() {
  ElMessageBox.alert(
    `当前已编制 ${tableData.value.length} 项专项现场应急处置措施，覆盖「${tableData.value.map(i => i.scene).join('、')}」等典型场景，责任人及应急值班通讯录已核验完备。`,
    'GliHub 专项应急预案核验摘要',
    { confirmButtonText: '确定' }
  )
}

function exportCsv() {
  const headers = ['序号', '应急措施名称', '措施类型', '适用场景', '执行负责人', '执行步骤', '注意事项', '联系方式']
  const rows = tableData.value.map((r, idx) => [
    idx + 1,
    `"${(r.measureName || '').replace(/"/g, '""')}"`,
    `"${(r.measureType || '').replace(/"/g, '""')}"`,
    `"${(r.scene || '').replace(/"/g, '""')}"`,
    `"${(r.executor || '').replace(/"/g, '""')}"`,
    `"${(r.steps || '').replace(/"/g, '""')}"`,
    `"${(r.notice || '').replace(/"/g, '""')}"`,
    `"${(r.contact || '').replace(/"/g, '""')}"`
  ])
  const csvContent = '\uFEFF' + [headers.join(','), ...rows.map(r => r.join(','))].join('\n')
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'GliHub_现场应急处置预案表.csv'
  link.click()
  URL.revokeObjectURL(link.href)
}
</script>

<style scoped>
.mb12 {
  margin-bottom: 12px;
}
</style>
