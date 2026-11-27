<template>
  <div class="app-container">
    <!-- 检索栏 -->
    <el-form :inline="true" :model="query" class="mb12">
      <el-form-item label="隐患标题">
        <el-input v-model="query.hazardTitle" placeholder="输入隐患内容搜索" clearable @keyup.enter="loadOrders" />
      </el-form-item>
      <el-form-item label="工单来源">
        <el-select v-model="query.sourceType" placeholder="全部来源" clearable style="width: 140px">
          <el-option label="AI视觉告警" value="VISION_AI" />
          <el-option label="人工专项排查" value="MANUAL" />
          <el-option label="安全检查表" value="SCL_CHECK" />
        </el-select>
      </el-form-item>
      <el-form-item label="闭环状态">
        <el-select v-model="query.status" placeholder="全部状态" clearable style="width: 140px">
          <el-option label="OPEN 待整改" value="OPEN" />
          <el-option label="RECTIFYING 整改中" value="RECTIFYING" />
          <el-option label="REVIEWING 待复核" value="REVIEWING" />
          <el-option label="CLOSED 已销项" value="CLOSED" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="loadOrders">查询</el-button>
        <el-button type="success" plain icon="Plus" @click="openCreateDialog">人工发起隐患工单</el-button>
      </el-form-item>
    </el-form>

    <!-- 工单列表 -->
    <el-table v-loading="loading" :data="orders" border>
      <el-table-column prop="orderNo" label="工单编号" width="170" />
      <el-table-column label="来源" width="110" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.sourceType === 'VISION_AI' ? 'danger' : 'info'">
            {{ row.sourceType }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="deptName" label="责任作业区" width="130" />
      <el-table-column prop="hazardTitle" label="隐患描述" min-width="210" />
      <el-table-column prop="riskLevel" label="隐患级别" width="100" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.riskLevel === '重大隐患' ? 'danger' : 'warning'">{{ row.riskLevel }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="legalBasis" label="触犯法规与标准依据" min-width="220" show-overflow-tooltip />
      <el-table-column prop="responsibleName" label="责任人" width="95" align="center" />
      <el-table-column label="闭环状态" width="120" align="center">
        <template #default="{ row }">
          <el-tag size="small" :type="row.status === 'CLOSED' ? 'success' : row.status === 'REVIEWING' ? 'warning' : 'danger'">
            {{ row.status }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="aiRecheckComment" label="AI 复查核验意见" min-width="200" show-overflow-tooltip />
      <el-table-column label="操作" width="150" align="center" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="row.status !== 'CLOSED'"
            link
            type="primary"
            icon="CircleCheck"
            @click="openRectifyDialog(row)"
          >提交复查核验</el-button>
          <el-tag v-else size="small" type="success">已闭环</el-tag>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="query.pageNum"
      v-model:limit="query.pageSize"
      @pagination="loadOrders"
    />

    <!-- 新增隐患工单弹窗（支持 RAG 自动引用法规） -->
    <el-dialog v-model="createOpen" title="新增隐患排查治理工单" width="600px" append-to-body>
      <el-form :model="form" label-width="110px">
        <el-form-item label="隐患标题">
          <el-input v-model="form.hazardTitle" placeholder="例如：储罐区防火堤东侧灭火器压力不足或通道占压" />
        </el-form-item>
        <el-form-item label="场所与作业区">
          <el-select v-model="form.placeType" style="width: 45%; margin-right: 4%">
            <el-option label="生产场所" value="production" />
            <el-option label="储存场所" value="storage" />
            <el-option label="公辅场所" value="auxiliary" />
          </el-select>
          <el-select v-model="form.deptId" style="width: 50%">
            <el-option v-for="d in depts" :key="d.deptId" :label="d.deptName" :value="d.deptId" />
          </el-select>
        </el-form-item>
        <el-form-item label="隐患级别">
          <el-radio-group v-model="form.riskLevel">
            <el-radio label="重大隐患">重大隐患</el-radio>
            <el-radio label="较大隐患">较大隐患</el-radio>
            <el-radio label="一般隐患">一般隐患</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="法规标准依据">
          <div style="display: flex; width: 100%; gap: 8px">
            <el-input v-model="form.legalBasis" placeholder="点击右侧按钮自动从向量知识库检索对应法条" />
            <el-button type="warning" plain @click="autoMatchLaw">RAG 匹配法条</el-button>
          </div>
        </el-form-item>
        <el-form-item label="整改措施要求">
          <el-input v-model="form.rectifyMeasure" type="textarea" :rows="2" />
        </el-form-item>
        <el-form-item label="整改责任人">
          <el-input v-model="form.responsibleName" placeholder="例如：注册安全员" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="createOpen = false">取 消</el-button>
        <el-button type="primary" @click="submitCreate">派发工单</el-button>
      </template>
    </el-dialog>

    <!-- 上传整改复查照片并触发 AI 核验闭环弹窗 -->
    <el-dialog v-model="rectifyOpen" title="提交隐患整改复查图像（AI 自动复检销项）" width="540px" append-to-body>
      <el-descriptions :column="1" border size="small" class="mb12">
        <el-descriptions-item label="工单编号">{{ activeOrder.orderNo }}</el-descriptions-item>
        <el-descriptions-item label="待整改隐患">{{ activeOrder.hazardTitle }}</el-descriptions-item>
      </el-descriptions>

      <el-form label-width="100px">
        <el-form-item label="整改说明">
          <el-input v-model="rectifyNote" type="textarea" :rows="2" placeholder="填写现场整改落实情况" />
        </el-form-item>
        <el-form-item label="复查图像">
          <el-upload
            :show-file-list="false"
            accept="image/*"
            :http-request="handleRectifyFileUpload"
          >
            <el-button type="primary" icon="Upload" :loading="rechecking">上传整改后照片并 AI 复核</el-button>
          </el-upload>
          <el-button
            type="success"
            plain
            class="ml8"
            :loading="rechecking"
            @click="handleRectifyBySample"
          >
            使用合规现场样本图快速验证销项
          </el-button>
        </el-form-item>
      </el-form>
    </el-dialog>
  </div>
</template>

<script setup name="HazardOrderLoop">
import { ElMessage } from 'element-plus'
import { listDept } from '@/api/system/dept'
import {
  listHazardOrders,
  createHazardOrder,
  submitRectifyUpload,
  submitRectifySample,
  recommendKbLaws
} from '@/api/ehs'

const loading = ref(false)
const rechecking = ref(false)
const total = ref(0)
const orders = ref([])
const depts = ref([])

const query = reactive({
  pageNum: 1,
  pageSize: 10,
  hazardTitle: '',
  sourceType: '',
  status: ''
})

const createOpen = ref(false)
const form = reactive({
  hazardTitle: '',
  placeType: 'production',
  deptId: 103,
  riskLevel: '较大隐患',
  legalBasis: '',
  rectifyMeasure: '',
  responsibleName: '注册安全员'
})

const rectifyOpen = ref(false)
const activeOrder = ref({})
const rectifyNote = ref('已完成现场违章纠偏与防护用品规范佩戴复查')

function loadOrders() {
  loading.value = true
  listHazardOrders(query)
    .then(res => {
      orders.value = res.rows || []
      total.value = res.total || 0
    })
    .finally(() => {
      loading.value = false
    })
}

function openCreateDialog() {
  form.hazardTitle = ''
  form.legalBasis = ''
  form.rectifyMeasure = ''
  createOpen.value = true
}

function autoMatchLaw() {
  if (!form.hazardTitle.trim()) {
    ElMessage.warning('请先填写隐患标题关键词以便检索对应法规')
    return
  }
  recommendKbLaws({ query: form.hazardTitle, placeType: form.placeType, topK: 2 }).then(res => {
    const items = res.data || []
    if (items.length) {
      form.legalBasis = items.map(i => `${i.doc_title || i.docTitle} ${i.clause_no || i.clauseNo}`).join('；')
      if (!form.rectifyMeasure) {
        form.rectifyMeasure = `严格依据 ${form.legalBasis} 要求立即落实整改并拍照复查。`
      }
      ElMessage.success('已自动匹配权威法规条款')
    }
  })
}

function submitCreate() {
  if (!form.hazardTitle.trim()) {
    ElMessage.warning('请填写隐患标题')
    return
  }
  createHazardOrder(form).then(() => {
    ElMessage.success('隐患工单派发成功')
    createOpen.value = false
    loadOrders()
  })
}

function openRectifyDialog(row) {
  activeOrder.value = { ...row }
  rectifyOpen.value = true
}

function handleRectifyFileUpload(options) {
  const fd = new FormData()
  fd.append('file', options.file)
  fd.append('rectifyNote', rectifyNote.value)
  rechecking.value = true
  submitRectifyUpload(activeOrder.value.orderId, fd)
    .then(res => {
      const comment = res.data?.aiRecheck?.review_comment || '复查完成'
      ElMessage.success(comment)
      rectifyOpen.value = false
      loadOrders()
    })
    .finally(() => {
      rechecking.value = false
    })
}

function handleRectifyBySample() {
  rechecking.value = true
  submitRectifySample(activeOrder.value.orderId, {
    sampleRelPath: 'archive/images/BikesHelmets0.png',
    rectifyNote: rectifyNote.value
  })
    .then(res => {
      ElMessage.success(res.data?.aiRecheck?.review_comment || 'AI 复检通过，工单已闭环销项')
      rectifyOpen.value = false
      loadOrders()
    })
    .finally(() => {
      rechecking.value = false
    })
}

onMounted(() => {
  loadOrders()
  listDept().then(res => {
    depts.value = (res.data || []).filter(d => d.parentId && Number(d.parentId) > 0)
  }).catch(() => {})
})
</script>

<style scoped>
.mb12 { margin-bottom: 12px; }
.ml8 { margin-left: 8px; }
</style>
