<template>
  <div class="app-container">
    <el-card shadow="never" class="mb16">
      <template #header>
        <div class="hdr-row">
          <span>插件化多模型视觉引擎注册表（兼容存量 YOLOv5 + YOLO26 + RF-DETR + YOLOE）</span>
          <el-button type="primary" size="small" icon="Plus" @click="openRegisterDialog">
            注册本地自定义 YOLOv5 权重
          </el-button>
        </div>
      </template>

      <el-table v-loading="loading" :data="modelList" border>
        <el-table-column prop="modelCode" label="模型编码" width="180" />
        <el-table-column prop="modelName" label="模型名称" min-width="220" />
        <el-table-column prop="adapterType" label="适配器架构" width="120" align="center">
          <template #default="{ row }">
            <el-tag size="small">{{ row.adapterType }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="weightsPath" label="权重挂载路径" min-width="240" show-overflow-tooltip />
        <el-table-column label="引擎实时状态" min-width="220">
          <template #default="{ row }">
            <el-tag size="small" :type="row.runtimeReady ? 'success' : 'info'" class="mr6">
              {{ row.runtimeReady ? '原生就绪' : '平滑降级待命' }}
            </el-tag>
            <span style="font-size: 12px; color: #606266">{{ row.runtimeMessage }}</span>
          </template>
        </el-table-column>
        <el-table-column label="置信度阈值" width="120" align="center">
          <template #default="{ row }">
            <el-input-number
              v-model="row.confThreshold"
              size="small"
              :min="0.1"
              :max="0.95"
              :step="0.05"
              :precision="2"
              @change="saveModelRow(row)"
            />
          </template>
        </el-table-column>
        <el-table-column label="VLM复核" width="90" align="center">
          <template #default="{ row }">
            <el-switch v-model="row.vlmReviewEnabled" @change="saveModelRow(row)" />
          </template>
        </el-table-column>
        <el-table-column label="默认引擎" width="95" align="center">
          <template #default="{ row }">
            <el-tag v-if="row.isDefault" type="success" size="small">默认</el-tag>
            <el-button v-else link type="primary" size="small" @click="setAsDefault(row)">设为默认</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-card shadow="never">
      <template #header>
        <div class="hdr-row">
          <span>厂区监控点位与作业场所绑定台账</span>
        </div>
      </template>
      <el-table :data="pointList" border size="small">
        <el-table-column prop="pointCode" label="点位编号" width="130" />
        <el-table-column prop="pointName" label="监控点位名称" min-width="200" />
        <el-table-column prop="deptName" label="所属作业区" width="150" />
        <el-table-column prop="placeType" label="场所类别" width="110" align="center" />
        <el-table-column prop="hazardName" label="覆盖危险源" min-width="180" />
        <el-table-column prop="defaultModelCode" label="默认调度模型" width="180" />
        <el-table-column label="平面坐标 (X%, Y%)" width="140" align="center">
          <template #default="{ row }">{{ row.mapX }}%, {{ row.mapY }}%</template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 注册新模型弹窗 -->
    <el-dialog v-model="dialogOpen" title="注册本地 YOLOv5 自定义权重 (.pt)" width="520px" append-to-body>
      <el-form :model="newForm" label-width="115px">
        <el-form-item label="模型唯一编码">
          <el-input v-model="newForm.modelCode" placeholder="例如：yolov5_helmet_last" />
        </el-form-item>
        <el-form-item label="模型显示名称">
          <el-input v-model="newForm.modelName" placeholder="例如：YOLOv5s 安全帽备选权重(last.pt)" />
        </el-form-item>
        <el-form-item label="本地权重路径">
          <el-input v-model="newForm.weightsPath" placeholder="../yolov5target-main/runs/train/exp15/weights/last.pt" />
        </el-form-item>
        <el-form-item label="默认置信度">
          <el-input-number v-model="newForm.confThreshold" :min="0.15" :max="0.9" :step="0.05" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogOpen = false">取 消</el-button>
        <el-button type="primary" @click="submitNewModel">注册并挂载</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="VisionModels">
import { ElMessage } from 'element-plus'
import { listVisionModels, addVisionModel, updateVisionModel, listCameraPoints } from '@/api/ehs'

const loading = ref(false)
const dialogOpen = ref(false)
const modelList = ref([])
const pointList = ref([])

const newForm = reactive({
  modelCode: '',
  modelName: '',
  adapterType: 'yolov5_local',
  weightsPath: '../yolov5target-main/runs/train/exp15/weights/last.pt',
  confThreshold: 0.35,
  vlmReviewEnabled: true
})

function fetchAll() {
  loading.value = true
  listVisionModels()
    .then(res => {
      modelList.value = res.data || []
    })
    .finally(() => {
      loading.value = false
    })
  listCameraPoints().then(res => {
    pointList.value = res.data || []
  })
}

function saveModelRow(row) {
  updateVisionModel(row).then(() => {
    ElMessage.success('模型参数已更新')
  })
}

function setAsDefault(row) {
  updateVisionModel({ ...row, isDefault: true }).then(() => {
    ElMessage.success(`已将 ${row.modelName} 设为默认视觉引擎`)
    fetchAll()
  })
}

function openRegisterDialog() {
  newForm.modelCode = ''
  newForm.modelName = ''
  dialogOpen.value = true
}

function submitNewModel() {
  if (!newForm.modelCode || !newForm.modelName || !newForm.weightsPath) {
    ElMessage.warning('请完整填写模型编码、名称与权重路径')
    return
  }
  addVisionModel(newForm).then(() => {
    ElMessage.success('自定义模型注册成功')
    dialogOpen.value = false
    fetchAll()
  })
}

onMounted(() => {
  fetchAll()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mr6 { margin-right: 6px; }
.hdr-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-weight: 600;
}
</style>
