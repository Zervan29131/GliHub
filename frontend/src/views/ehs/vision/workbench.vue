<template>
  <div class="app-container">
    <!-- 顶部检测引擎与参数控制台 -->
    <el-card shadow="never" class="mb16">
      <template #header>
        <div class="bar-hdr">
          <span>智能视觉监控与「Stage-1 检测 + Stage-2 VLM 复核」双阶段研判台</span>
          <el-tag type="primary">默认纳管 yolov5target-main 自训安全帽模型</el-tag>
        </div>
      </template>

      <el-form :inline="true" label-width="96px">
        <el-form-item label="监控点位">
          <el-select v-model="ctrl.pointId" placeholder="绑定监控点位" clearable style="width: 220px" @change="onPointChange">
            <el-option
              v-for="p in cameraPoints"
              :key="p.pointId"
              :label="`${p.pointName} (${p.deptName || ''})`"
              :value="p.pointId"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="场所类别">
          <el-select v-model="ctrl.placeType" style="width: 140px">
            <el-option label="生产场所" value="production" />
            <el-option label="储存场所" value="storage" />
            <el-option label="公辅场所" value="auxiliary" />
          </el-select>
        </el-form-item>

        <el-form-item label="视觉引擎">
          <el-select v-model="ctrl.modelCode" style="width: 290px">
            <el-option
              v-for="m in models"
              :key="m.modelCode"
              :label="`${m.modelName} [${m.adapterType}]`"
              :value="m.modelCode"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="置信度阈值">
          <el-input-number v-model="ctrl.confThres" :min="0.15" :max="0.9" :step="0.05" :precision="2" style="width: 125px" />
        </el-form-item>

        <el-form-item label="VLM 二次复核">
          <el-switch v-model="ctrl.enableVlm" active-text="开启" inactive-text="仅初筛" />
        </el-form-item>

        <el-form-item v-if="ctrl.modelCode === 'yoloe_zero_shot' || showPromptInput" label="开放词汇提示" style="width: 100%">
          <el-input
            v-model="ctrl.promptText"
            placeholder="输入自然语言排查目标（英文或中文逗号分隔），例如：未佩戴安全帽, 厂区通勤车, 玩手机, 敞口化学品桶"
            clearable
            style="width: 620px"
          />
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 主体：左侧样本/上传与框选画布，右侧 VLM 语义复核 + 法规引用 + 自动派单 -->
    <el-row :gutter="16" class="mb16">
      <el-col :xs="24" :lg="13">
        <el-card shadow="never">
          <template #header>
            <div class="bar-hdr">
              <span>现场抓拍上传 &amp; 存量测试样本一键研判</span>
              <el-upload
                :show-file-list="false"
                accept="image/*"
                :http-request="handleCustomUpload"
              >
                <el-button type="primary" size="small" icon="Upload" :loading="analyzing">上传现场抓拍图检测</el-button>
              </el-upload>
            </div>
          </template>

          <!-- 内置样本快捷栏 -->
          <div class="sample-strip mb12">
            <span class="strip-label">内置样本库：</span>
            <el-button
              v-for="sp in builtInSamples"
              :key="sp.relPath"
              size="small"
              plain
              :type="activeSample === sp.relPath ? 'primary' : 'default'"
              :loading="analyzing && activeSample === sp.relPath"
              @click="runSampleDetect(sp)"
            >
              {{ sp.title }}
            </el-button>
          </div>

          <!-- 标注画布预览 -->
          <div v-loading="analyzing" class="canvas-stage">
            <el-empty v-if="!currentOutput.imageUrl" description="点击上方任意内置样本或上传现场图像，体验毫秒级目标检测 + VLM 复核" />
            <div v-else class="stage-img-wrap">
              <img :src="currentOutput.imageUrl" alt="AI Detection Output" class="stage-img" />
              <div class="stage-meta">
                <span>引擎：<b>{{ currentOutput.vision?.model_code }}</b></span>
                <span>推理耗时：<b>{{ currentOutput.vision?.inference_ms || 0 }} ms</b></span>
                <span>检出目标：<b>{{ (currentOutput.vision?.detections || []).length }} 个</b></span>
              </div>
            </div>
          </div>

          <!-- 第一阶段候选框明细 -->
          <el-table
            v-if="currentOutput.vision?.detections?.length"
            :data="currentOutput.vision.detections"
            size="small"
            border
            class="mt12"
          >
            <el-table-column prop="label_zh" label="检出目标类别" width="160" />
            <el-table-column prop="confidence" label="置信度" width="90" align="center" />
            <el-table-column label="像素坐标 [x1, y1, x2, y2]">
              <template #default="{ row }">
                {{ row.bbox_xyxy.map(n => Math.round(n)).join(', ') }}
              </template>
            </el-table-column>
            <el-table-column label="初筛属性" width="100" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.is_violation ? 'danger' : 'success'">
                  {{ row.is_violation ? '违章候选' : '合规目标' }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="11">
        <el-card shadow="never">
          <template #header>
            <div class="bar-hdr">
              <span>Stage-2 VLM 多模态复核结论与法规闭环</span>
              <el-tag v-if="currentOutput.vlmReview" :type="currentOutput.vlmReview.is_real_hazard ? 'danger' : 'success'">
                {{ currentOutput.vlmReview.is_real_hazard ? '确认真实隐患' : '合规 / 误报已过滤' }}
              </el-tag>
            </div>
          </template>

          <el-empty v-if="!currentOutput.alert" description="等待视觉研判结果..." />
          <div v-else>
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="告警单号">{{ currentOutput.alert.alertNo }}</el-descriptions-item>
              <el-descriptions-item label="复核引擎">{{ currentOutput.vlmReview?.vlm_model || 'Stage-1 初筛模式' }}</el-descriptions-item>
              <el-descriptions-item label="隐患定性">
                <strong>{{ currentOutput.alert.violationType }}</strong>
              </el-descriptions-item>
              <el-descriptions-item label="风险严重度">
                <el-tag size="small" :type="severityTag(currentOutput.alert.severity)">
                  {{ currentOutput.alert.severity }}
                </el-tag>
              </el-descriptions-item>
              <el-descriptions-item label="VLM 语义研判">{{ currentOutput.alert.vlmDescription }}</el-descriptions-item>
              <el-descriptions-item label="初步整改建议">{{ currentOutput.alert.vlmSuggestion || '按岗位规程常态巡检' }}</el-descriptions-item>
            </el-descriptions>

            <!-- RAG 法规引用 -->
            <div v-if="currentOutput.citedLaws && currentOutput.citedLaws.length" class="law-panel mt12">
              <div class="law-title">RAG 自动匹配触犯法规与国标条款：</div>
              <div v-for="(law, i) in currentOutput.citedLaws" :key="i" class="law-card">
                <div class="law-head">{{ law.doc_title }} · {{ law.clause_no }}</div>
                <div class="law-body">{{ law.chunk_text }}</div>
              </div>
            </div>

            <!-- 隐患工单闭环动作 -->
            <div class="order-action-bar mt12">
              <el-alert
                v-if="currentOutput.autoCreatedOrder"
                type="warning"
                show-icon
                :closable="false"
                :title="`已自动派发隐患整改工单：${currentOutput.autoCreatedOrder.orderNo}（责任人：${currentOutput.autoCreatedOrder.responsibleName}）`"
              />
              <div class="mt10">
                <el-button
                  v-if="currentOutput.autoCreatedOrder || currentOutput.alert.orderId"
                  type="primary"
                  size="small"
                  icon="Right"
                  @click="router.push('/vision-loop/orders')"
                >
                  前往隐患闭环工单核查
                </el-button>
                <el-button
                  v-else-if="currentOutput.alert.isRealHazard"
                  type="danger"
                  size="small"
                  icon="DocumentAdd"
                  @click="manualCreateOrder(currentOutput.alert.alertId)"
                >
                  一键生成隐患治理工单
                </el-button>
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 底部：视觉告警历史流水台账 -->
    <el-card shadow="never">
      <template #header>
        <div class="bar-hdr">
          <span>视觉监控复核告警历史记录</span>
          <el-button size="small" icon="Refresh" @click="loadAlertList">刷新列表</el-button>
        </div>
      </template>

      <el-table :data="alertRows" border size="small">
        <el-table-column prop="alertNo" label="告警编号" width="175" />
        <el-table-column label="标注图" width="90" align="center">
          <template #default="{ row }">
            <el-image
              v-if="row.annotatedImageUrl"
              :src="resolveUrl(row.annotatedImageUrl)"
              :preview-src-list="[resolveUrl(row.annotatedImageUrl)]"
              preview-teleported
              style="width: 58px; height: 38px; border-radius: 4px"
              fit="cover"
            />
          </template>
        </el-table-column>
        <el-table-column prop="deptName" label="所属作业区" width="125" />
        <el-table-column prop="modelCode" label="调用模型" width="155" />
        <el-table-column prop="violationType" label="研判定性" width="160" />
        <el-table-column label="严重度" width="85" align="center">
          <template #default="{ row }">
            <el-tag size="small" :type="severityTag(row.severity)">{{ row.severity }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="vlmDescription" label="VLM 复核说明" min-width="240" show-overflow-tooltip />
        <el-table-column prop="handleStatus" label="状态" width="140" align="center" />
        <el-table-column label="操作" width="160" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.handleStatus === 'PENDING' && row.isRealHazard"
              link
              type="primary"
              size="small"
              @click="manualCreateOrder(row.alertId)"
            >转工单</el-button>
            <el-button
              v-if="row.handleStatus === 'PENDING'"
              link
              type="info"
              size="small"
              @click="handleDismiss(row.alertId)"
            >忽略误报</el-button>
            <el-button
              v-if="row.orderId"
              link
              type="success"
              size="small"
              @click="router.push('/vision-loop/orders')"
            >查看工单</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup name="VisionWorkbench">
import { ElMessage } from 'element-plus'
import {
  listVisionModels,
  listCameraPoints,
  listBuiltInSamples,
  detectBySample,
  detectByUpload,
  listVisionAlerts,
  convertAlertToOrder,
  dismissVisionAlert,
  resolveBackendAssetUrl
} from '@/api/ehs'

const router = useRouter()
const analyzing = ref(false)
const showPromptInput = ref(false)
const activeSample = ref('')

const models = ref([])
const cameraPoints = ref([])
const builtInSamples = ref([])
const alertRows = ref([])

const ctrl = reactive({
  pointId: null,
  deptId: 103,
  placeType: 'production',
  modelCode: 'yolov5_helmet_local',
  promptText: '未佩戴安全帽, 通勤车',
  confThres: 0.35,
  enableVlm: true
})

const currentOutput = reactive({
  imageUrl: '',
  alert: null,
  vision: null,
  vlmReview: null,
  citedLaws: [],
  autoCreatedOrder: null
})

function resolveUrl(u) {
  return resolveBackendAssetUrl(u)
}

function severityTag(sev) {
  if (sev === 'CRITICAL' || sev === 'HIGH') return 'danger'
  if (sev === 'MEDIUM') return 'warning'
  return 'success'
}

function onPointChange(ptId) {
  const found = cameraPoints.value.find(p => p.pointId === ptId)
  if (found) {
    ctrl.deptId = found.deptId
    ctrl.placeType = found.placeType
    if (found.defaultModelCode) {
      ctrl.modelCode = found.defaultModelCode
    }
  }
}

function bindDetectionResponse(data) {
  currentOutput.alert = data.alert
  currentOutput.vision = data.vision
  currentOutput.vlmReview = data.vlmReview
  currentOutput.citedLaws = data.citedLaws || []
  currentOutput.autoCreatedOrder = data.autoCreatedOrder || null
  currentOutput.imageUrl = resolveUrl(data.alert?.annotatedImageUrl || data.alert?.rawImageUrl)
  loadAlertList()
}

function runSampleDetect(sp) {
  activeSample.value = sp.relPath
  ctrl.placeType = sp.placeType || ctrl.placeType
  analyzing.value = true
  detectBySample({
    sampleRelPath: sp.relPath,
    pointId: ctrl.pointId,
    deptId: ctrl.deptId,
    placeType: ctrl.placeType,
    modelCode: ctrl.modelCode,
    promptText: ctrl.modelCode === 'yoloe_zero_shot' ? ctrl.promptText : undefined,
    confThres: ctrl.confThres,
    enableVlm: ctrl.enableVlm
  })
    .then(res => {
      if (res && res.data) {
        bindDetectionResponse(res.data)
        ElMessage.success('视觉检测与 VLM 复核完成')
      }
    })
    .finally(() => {
      analyzing.value = false
    })
}

function handleCustomUpload(options) {
  const fd = new FormData()
  fd.append('file', options.file)
  if (ctrl.pointId) fd.append('pointId', ctrl.pointId)
  if (ctrl.deptId) fd.append('deptId', ctrl.deptId)
  fd.append('placeType', ctrl.placeType)
  fd.append('modelCode', ctrl.modelCode)
  if (ctrl.promptText) fd.append('promptText', ctrl.promptText)
  fd.append('confThres', ctrl.confThres)
  fd.append('enableVlm', ctrl.enableVlm)

  analyzing.value = true
  detectByUpload(fd)
    .then(res => {
      if (res && res.data) {
        bindDetectionResponse(res.data)
        ElMessage.success('上传图像研判完成')
      }
    })
    .finally(() => {
      analyzing.value = false
    })
}

function manualCreateOrder(alertId) {
  convertAlertToOrder(alertId).then(res => {
    ElMessage.success(`已生成隐患治理工单：${res.data?.orderNo || ''}`)
    if (currentOutput.alert && currentOutput.alert.alertId === alertId) {
      currentOutput.autoCreatedOrder = res.data
    }
    loadAlertList()
  })
}

function handleDismiss(alertId) {
  dismissVisionAlert(alertId).then(() => {
    ElMessage.info('已标记为误报忽略')
    loadAlertList()
  })
}

function loadAlertList() {
  listVisionAlerts({ pageNum: 1, pageSize: 10 }).then(res => {
    alertRows.value = res.rows || []
  })
}

onMounted(() => {
  listVisionModels().then(res => {
    models.value = res.data || []
  })
  listCameraPoints().then(res => {
    cameraPoints.value = res.data || []
    if (cameraPoints.value.length) {
      ctrl.pointId = cameraPoints.value[0].pointId
    }
  })
  listBuiltInSamples().then(res => {
    builtInSamples.value = res.data || []
  })
  loadAlertList()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mb12 { margin-bottom: 12px; }
.mt12 { margin-top: 12px; }
.mt10 { margin-top: 10px; }
.bar-hdr {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
.sample-strip {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}
.strip-label {
  font-size: 13px;
  color: #606266;
  font-weight: 600;
}
.canvas-stage {
  min-height: 280px;
  background: #141a24;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px;
}
.stage-img-wrap {
  width: 100%;
  text-align: center;
}
.stage-img {
  max-width: 100%;
  max-height: 360px;
  border-radius: 4px;
}
.stage-meta {
  display: flex;
  justify-content: center;
  gap: 20px;
  margin-top: 8px;
  color: #dcdfe6;
  font-size: 12px;
}
.law-panel {
  background: #fdf6ec;
  border: 1px solid #faecd8;
  border-radius: 6px;
  padding: 10px 12px;
}
.law-title {
  font-size: 13px;
  font-weight: 600;
  color: #b88230;
  margin-bottom: 6px;
}
.law-card {
  margin-bottom: 6px;
}
.law-head {
  font-size: 12px;
  font-weight: 600;
  color: #303133;
}
.law-body {
  font-size: 12px;
  color: #606266;
}
</style>
