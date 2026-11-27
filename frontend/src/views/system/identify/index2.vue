<template>
  <div class="app-container">
    <el-form :inline="true" class="mb8">
      <el-form-item label="危险源检索">
        <el-input
          v-model="search"
          placeholder="输入危险源名称、所在作业区或危险特性检索"
          clearable
          style="width: 300px"
        />
      </el-form-item>
      <el-form-item>
        <el-button
          type="primary"
          plain
          icon="Plus"
          @click="handleAdd"
          v-hasPermi="['system:notice:add']"
        >新增危险源</el-button>
      </el-form-item>
    </el-form>

    <el-table
      :data="filteredHazards"
      border
      style="width: 100%"
      :header-cell-style="{ 'text-align': 'center' }"
    >
      <el-table-column label="序号" width="80" type="index" align="center" />
      <el-table-column label="主要危险源" width="220" prop="type" align="center" />
      <el-table-column label="所在区域与设备关联信息" min-width="320" prop="location" align="center" />
      <el-table-column label="危险特性与可能后果" min-width="260" prop="remark" align="center" />
      <el-table-column label="风险管控等级" width="130" align="center">
        <template #default="{ row }">
          <el-tag :type="row.level === '重大风险' ? 'danger' : row.level === '较大风险' ? 'warning' : 'info'">
            {{ row.level }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column align="center" label="操作" width="180">
        <template #default="scope">
          <el-button
            link
            type="primary"
            icon="View"
            @click="handleDetail(scope.row)"
          >详情</el-button>
          <el-button
            link
            type="danger"
            icon="Delete"
            @click="handleDelete(scope.$index)"
            v-hasPermi="['system:notice:remove']"
          >删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 危险源详情对话框 -->
    <el-dialog v-model="detailVisible" title="危险源档案详情" width="580px" append-to-body>
      <el-descriptions :column="1" border>
        <el-descriptions-item label="主要危险源">{{ currentRow.type }}</el-descriptions-item>
        <el-descriptions-item label="所在区域与关联设施">{{ currentRow.location }}</el-descriptions-item>
        <el-descriptions-item label="风险等级">{{ currentRow.level }}</el-descriptions-item>
        <el-descriptions-item label="危险特性">{{ currentRow.remark }}</el-descriptions-item>
        <el-descriptions-item label="现场应急处置要点">{{ currentRow.measure }}</el-descriptions-item>
      </el-descriptions>
      <template #footer>
        <el-button type="primary" @click="detailVisible = false">关 闭</el-button>
      </template>
    </el-dialog>

    <!-- 新增危险源对话框 -->
    <el-dialog v-model="addVisible" title="新增危险源档案" width="560px" append-to-body>
      <el-form :model="form" label-width="120px">
        <el-form-item label="主要危险源">
          <el-input v-model="form.type" placeholder="例如：甲醇储罐区 / 一氧化碳管线" />
        </el-form-item>
        <el-form-item label="所在作业区域">
          <el-input v-model="form.location" placeholder="例如：采油作业区二号增压站" />
        </el-form-item>
        <el-form-item label="风险等级">
          <el-select v-model="form.level" style="width: 100%">
            <el-option label="重大风险" value="重大风险" />
            <el-option label="较大风险" value="较大风险" />
            <el-option label="一般风险" value="一般风险" />
          </el-select>
        </el-form-item>
        <el-form-item label="危险特性描述">
          <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="描述易燃易爆、中毒窒息或高压危害特性" />
        </el-form-item>
        <el-form-item label="应急处置要点">
          <el-input v-model="form.measure" type="textarea" :rows="2" placeholder="填写泄漏切断、通风及个体防护要求" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addVisible = false">取 消</el-button>
        <el-button type="primary" @click="confirmAdd">确 定</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="HazardDetail">
import { ElMessage, ElMessageBox } from 'element-plus'

const search = ref('')
const detailVisible = ref(false)
const addVisible = ref(false)
const currentRow = ref({})

const hazardList = ref([
  {
    id: 1,
    type: '一氧化碳（CO）工艺管线',
    location: '采油作业区一号联合站与合成气装置区',
    remark: '易燃易爆有毒气体，与空气混合能形成爆炸性混合物（爆炸极限 12.5%~74.2%），吸入可致急性中毒窒息。',
    level: '重大风险',
    measure: '佩戴正压式空气呼吸器，立即切断气源阀门，开启事故排风与水幕稀释，严禁明火及非防爆工具操作。'
  },
  {
    id: 2,
    type: '压力容器与高压集输管道',
    location: '采油作业区至油气矿仪陇作业区输气干线',
    remark: '长期受高压及介质腐蚀影响，若法兰密封失效或超压破损将引发物理爆炸及次生火灾爆炸。',
    level: '重大风险',
    measure: '触发SIS紧急切断阀隔离上下游管段，划定警戒区疏散下风向人员，使用雾状水冷却毗邻设备。'
  },
  {
    id: 3,
    type: '甲醇常压立式储罐组',
    location: '储存场所一号危化品罐区',
    remark: '甲类易燃液体，闪点 11℃，蒸气比空气重，能在较低处扩散到相当远的地方遇火源回燃。',
    level: '较大风险',
    measure: '依托防火堤围堵泄漏液，开启抗溶性泡沫灭火系统覆盖液面，切断罐区周边电源。'
  },
  {
    id: 4,
    type: '中心变配电站高压开关柜',
    location: '公辅场所一号变配电室',
    remark: '绝缘老化或误操作易引发弧光短路、触电伤亡及电气火灾事故。',
    level: '一般风险',
    measure: '严格执行停电、验电、挂接地线制度；发生火情先断电并使用二氧化碳灭火器扑救。'
  }
])

const filteredHazards = computed(() => {
  const kw = search.value.trim().toLowerCase()
  if (!kw) return hazardList.value
  return hazardList.value.filter(item =>
    item.type.toLowerCase().includes(kw) ||
    item.location.toLowerCase().includes(kw) ||
    item.remark.toLowerCase().includes(kw)
  )
})

const form = reactive({
  type: '',
  location: '',
  level: '较大风险',
  remark: '',
  measure: ''
})

function handleDetail(row) {
  currentRow.value = { ...row }
  detailVisible.value = true
}

function handleAdd() {
  form.type = ''
  form.location = ''
  form.level = '较大风险'
  form.remark = ''
  form.measure = ''
  addVisible.value = true
}

function confirmAdd() {
  if (!form.type.trim() || !form.location.trim()) {
    ElMessage.warning('请填写主要危险源名称及所在作业区域')
    return
  }
  hazardList.value.push({
    id: Date.now(),
    type: form.type.trim(),
    location: form.location.trim(),
    level: form.level,
    remark: form.remark.trim() || '易燃易爆或特种设备安全风险',
    measure: form.measure.trim() || '按照现场专项应急处置方案执行隔离与疏散'
  })
  addVisible.value = false
  ElMessage.success('危险源档案新增成功')
}

function handleDelete(index) {
  ElMessageBox.confirm('确认删除该条危险源记录吗？', '系统提示', { type: 'warning' })
    .then(() => {
      hazardList.value.splice(index, 1)
      ElMessage.success('删除成功')
    })
    .catch(() => {})
}
</script>
