<template>
  <div class="app-container">
    <el-alert
      title="边缘计算自治模式：独立 edge-yolo26 节点无需连接 PostgreSQL/Valkey，断网时告警暂存本地 SQLite WAL 环形缓存，联网后按 alertUuid 幂等补传至中台。"
      type="info"
      show-icon
      :closable="false"
      class="mb16"
    />

    <!-- 边缘节点卡片矩阵 -->
    <el-row :gutter="16" class="mb16">
      <el-col v-for="node in nodes" :key="node.node_code" :xs="24" :md="12" :lg="8">
        <el-card shadow="hover" class="edge-card" :class="{ active: selectedNode?.node_code === node.node_code }" @click="selectNode(node)">
          <div class="edge-hdr">
            <div>
              <strong>{{ node.node_name }}</strong>
              <div class="sub-code">{{ node.node_code }} · {{ node.chip_model || node.os_arch }}</div>
            </div>
            <el-tag :type="node.online_status === 'ONLINE' ? 'success' : 'info'" effect="dark" size="small">
              {{ node.online_status }}
            </el-tag>
          </div>
          <div class="edge-metrics">
            <div><span class="lbl">推理精度</span><b>{{ (node.precision_mode || 'int8').toUpperCase() }}</b></div>
            <div><span class="lbl">实时帧率</span><b class="text-primary">{{ node.current_fps || 0 }} FPS</b></div>
            <div><span class="lbl">常驻内存</span><b>{{ node.mem_mb || 0 }} MB</b></div>
            <div><span class="lbl">断网待传</span><b :class="node.offline_queue_size > 0 ? 'text-warning' : 'text-success'">{{ node.offline_queue_size || 0 }} 条</b></div>
          </div>
          <div class="edge-foot">
            <span>当前模型：<code>{{ node.active_model_code }}</code> (v{{ node.config_version }})</span>
            <el-link v-if="node.local_debug_url" :href="node.local_debug_url" target="_blank" type="primary" @click.stop>
              打开 :8091 调试台
            </el-link>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <!-- 左侧：Canvas 多边形电子围栏 (Polygon ROI) 绘制台 -->
      <el-col :xs="24" :lg="15">
        <el-card shadow="never">
          <template #header>
            <div class="hdr-between">
              <span>可视化电子围栏（Polygon ROI）框选与 YOLO26 四任务下发</span>
              <div>
                <el-button size="small" @click="resetFullFrameRoi">重置全画幅</el-button>
                <el-button size="small" type="warning" plain @click="clearVertices">清空重绘</el-button>
                <el-button size="small" type="primary" :loading="savingRoi" @click="handleSaveRoi">
                  保存并同步至边缘节点
                </el-button>
              </div>
            </div>
          </template>

          <el-form :inline="true" size="small" class="mb12">
            <el-form-item label="绑定通道">
              <el-select v-model="roiForm.channelCode" style="width: 185px" @change="onChannelChange">
                <el-option
                  v-for="ch in currentChannels"
                  :key="ch.channel_code"
                  :label="`${ch.channel_name} (${ch.channel_code})`"
                  :value="ch.channel_code"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="YOLO26 任务模式">
              <el-select v-model="roiForm.taskType" style="width: 175px">
                <el-option label="Detect (无NMS违章检测)" value="detect" />
                <el-option label="Pose (17关键点跌倒/高空)" value="pose" />
                <el-option label="Seg (跑冒滴漏像素掩码)" value="seg" />
                <el-option label="OBB (旋转框仪表/槽车)" value="obb" />
              </el-select>
            </el-form-item>
            <el-form-item label="置信度">
              <el-input-number v-model="roiForm.confThreshold" :min="0.15" :max="0.9" :step="0.05" />
            </el-form-item>
            <el-form-item label="底图预览">
              <el-select v-model="bgSampleUrl" style="width: 170px" @change="loadCanvasBg">
                <el-option v-for="s in samples" :key="s.url" :label="s.title.slice(0, 12)" :value="s.url" />
              </el-select>
            </el-form-item>
          </el-form>

          <div class="canvas-box">
            <canvas ref="roiCanvasRef" width="760" height="430" class="roi-canvas" @click="onCanvasClick" />
          </div>
          <div class="roi-hint">
            提示：直接在上方监控底图点击鼠标添加多边形电子围栏顶点（已选 <b>{{ roiForm.roiPolygon.length }}</b> 个顶点），保存后自动递增节点 <code>config_version</code>，边缘盒子在下一轮心跳自动热更新围栏。
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：SHA256 低精度模型 OTA 远程下发 -->
      <el-col :xs="24" :lg="9">
        <el-card shadow="never">
          <template #header>
            <div class="hdr-between">
              <span>低精度 ONNX 模型远程 OTA 热更新（SHA256 校验）</span>
              <el-button size="small" icon="Refresh" @click="fetchAll">刷新</el-button>
            </div>
          </template>

          <el-form label-position="top" size="small">
            <el-form-item label="选择中心 ./data/models 量化模型包">
              <el-select v-model="otaForm.targetModelFile" style="width: 100%">
                <el-option
                  v-for="m in otaModels"
                  :key="m.fileName"
                  :label="`${m.fileName} (${m.precision.toUpperCase()} · ${m.sizeMb} MB)`"
                  :value="m.fileName"
                />
              </el-select>
            </el-form-item>
            <div v-if="selectedOtaModel" class="sha-box">
              <div>精度格式：<el-tag size="small">{{ selectedOtaModel.precision.toUpperCase() }}</el-tag> · 体积：<b>{{ selectedOtaModel.sizeMb }} MB</b></div>
              <div class="sha-line">SHA256：<code>{{ selectedOtaModel.sha256 }}</code></div>
            </div>
            <el-button type="primary" style="width: 100%; margin-top: 10px" :loading="pushingOta" @click="handlePushOta">
              向节点「{{ selectedNode?.node_code || 'edge-chem-zone-01' }}」下发原子热更新指令
            </el-button>
          </el-form>

          <el-divider content-position="left">近期 OTA 下发流水</el-divider>
          <el-empty v-if="!currentOtaHistory.length" description="暂无 OTA 下发记录" :image-size="60" />
          <el-table v-else :data="currentOtaHistory" size="small" border>
            <el-table-column prop="target_model_file" label="模型文件" min-width="145" />
            <el-table-column prop="ota_status" label="状态" width="95" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="row.ota_status === 'APPLIED' ? 'success' : 'warning'">{{ row.ota_status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="SHA256摘要" width="105">
              <template #default="{ row }">
                <code>{{ (row.sha256_hex || '').slice(0, 10) }}...</code>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup name="EhsEdgeCenter">
import { ElMessage } from 'element-plus'
import {
  listBuiltInSamples,
  listEdgeNodes,
  listEdgeOtaModels,
  pushEdgeOtaModel,
  resolveBackendAssetUrl,
  updateEdgeChannelRoi
} from '@/api/ehs'

const nodes = ref([])
const selectedNode = ref(null)
const otaModels = ref([])
const samples = ref([])
const bgSampleUrl = ref('')
const savingRoi = ref(false)
const pushingOta = ref(false)
const roiCanvasRef = ref(null)
let bgImageObj = null

const roiForm = reactive({
  channelCode: 'cam-tank-01',
  taskType: 'detect',
  confThreshold: 0.35,
  roiPolygon: [
    [0.05, 0.05],
    [0.95, 0.05],
    [0.95, 0.95],
    [0.05, 0.95]
  ]
})

const otaForm = reactive({
  targetModelFile: 'yolo26n.int8.onnx'
})

const currentChannels = computed(() => selectedNode.value?.channels || [])
const currentOtaHistory = computed(() => selectedNode.value?.otaHistory || [])
const selectedOtaModel = computed(() => otaModels.value.find(m => m.fileName === otaForm.targetModelFile))

function selectNode(node) {
  selectedNode.value = node
  if (node.channels && node.channels.length) {
    const ch = node.channels[0]
    roiForm.channelCode = ch.channel_code
    roiForm.taskType = ch.task_type || 'detect'
    roiForm.confThreshold = Number(ch.conf_threshold || 0.35)
    roiForm.roiPolygon = Array.isArray(ch.roiPolygon) && ch.roiPolygon.length >= 3
      ? ch.roiPolygon.map(p => [Number(p[0]), Number(p[1])])
      : [[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]]
    drawCanvas()
  }
}

function onChannelChange(code) {
  const ch = currentChannels.value.find(c => c.channel_code === code)
  if (ch) {
    roiForm.taskType = ch.task_type || 'detect'
    roiForm.confThreshold = Number(ch.conf_threshold || 0.35)
    if (Array.isArray(ch.roiPolygon) && ch.roiPolygon.length >= 3) {
      roiForm.roiPolygon = ch.roiPolygon.map(p => [Number(p[0]), Number(p[1])])
    }
    drawCanvas()
  }
}

function loadCanvasBg() {
  if (!bgSampleUrl.value) return
  const im = new Image()
  im.crossOrigin = 'anonymous'
  im.onload = () => {
    bgImageObj = im
    drawCanvas()
  }
  im.src = resolveBackendAssetUrl(bgSampleUrl.value)
}

function drawCanvas() {
  const canvas = roiCanvasRef.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  if (bgImageObj) {
    ctx.drawImage(bgImageObj, 0, 0, canvas.width, canvas.height)
  } else {
    ctx.fillStyle = '#101827'
    ctx.fillRect(0, 0, canvas.width, canvas.height)
  }

  const pts = roiForm.roiPolygon
  if (pts.length > 0) {
    ctx.save()
    ctx.beginPath()
    pts.forEach((p, idx) => {
      const x = p[0] * canvas.width
      const y = p[1] * canvas.height
      if (idx === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    if (pts.length >= 3) {
      ctx.closePath()
      ctx.fillStyle = 'rgba(0, 212, 255, 0.18)'
      ctx.fill()
    }
    ctx.lineWidth = 2.5
    ctx.strokeStyle = '#00e5ff'
    ctx.stroke()

    pts.forEach((p, idx) => {
      const x = p[0] * canvas.width
      const y = p[1] * canvas.height
      ctx.fillStyle = '#ffca28'
      ctx.beginPath()
      ctx.arc(x, y, 5, 0, Math.PI * 2)
      ctx.fill()
      ctx.fillStyle = '#fff'
      ctx.font = '12px sans-serif'
      ctx.fillText(`P${idx + 1}`, x + 7, y - 6)
    })
    ctx.restore()
  }
}

function onCanvasClick(e) {
  const canvas = roiCanvasRef.value
  const rect = canvas.getBoundingClientRect()
  const nx = Number(((e.clientX - rect.left) / rect.width).toFixed(3))
  const ny = Number(((e.clientY - rect.top) / rect.height).toFixed(3))
  roiForm.roiPolygon.push([nx, ny])
  drawCanvas()
}

function clearVertices() {
  roiForm.roiPolygon = []
  drawCanvas()
}

function resetFullFrameRoi() {
  roiForm.roiPolygon = [[0.05, 0.05], [0.95, 0.05], [0.95, 0.95], [0.05, 0.95]]
  drawCanvas()
}

function handleSaveRoi() {
  if (roiForm.roiPolygon.length < 3) {
    ElMessage.warning('请至少在画布点击 3 个顶点构成闭合电子围栏')
    return
  }
  savingRoi.value = true
  updateEdgeChannelRoi({
    nodeCode: selectedNode.value?.node_code || 'edge-chem-zone-01',
    channelCode: roiForm.channelCode,
    taskType: roiForm.taskType,
    confThreshold: roiForm.confThreshold,
    roiPolygon: roiForm.roiPolygon
  })
    .then(res => {
      ElMessage.success(`电子围栏已保存，配置版本升至 v${res.data?.configVersion || ''}`)
      fetchAll()
    })
    .finally(() => {
      savingRoi.value = false
    })
}

function handlePushOta() {
  pushingOta.value = true
  pushEdgeOtaModel({
    nodeCode: selectedNode.value?.node_code || 'edge-chem-zone-01',
    targetModelFile: otaForm.targetModelFile
  })
    .then(res => {
      ElMessage.success(`OTA 任务 #${res.data?.otaId} 已入队，边缘节点将在下次心跳校验 SHA256 并原子热重载`)
      fetchAll()
    })
    .finally(() => {
      pushingOta.value = false
    })
}

function fetchAll() {
  Promise.all([listEdgeNodes(), listEdgeOtaModels(), listBuiltInSamples()]).then(([nRes, mRes, sRes]) => {
    nodes.value = nRes.data || []
    if (nodes.value.length && !selectedNode.value) {
      selectNode(nodes.value[0])
    } else if (selectedNode.value) {
      const updated = nodes.value.find(x => x.node_code === selectedNode.value.node_code)
      if (updated) selectedNode.value = updated
    }
    otaModels.value = mRes.data || []
    if (otaModels.value.length && !otaForm.targetModelFile) {
      otaForm.targetModelFile = otaModels.value[0].fileName
    }
    samples.value = sRes.data || []
    if (samples.value.length && !bgSampleUrl.value) {
      bgSampleUrl.value = samples.value[0].url
      loadCanvasBg()
    } else {
      nextTick(drawCanvas)
    }
  })
}

onMounted(() => {
  fetchAll()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mb12 { margin-bottom: 12px; }
.hdr-between { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.edge-card { cursor: pointer; border: 1px solid #ebeef5; transition: all 0.2s; }
.edge-card.active { border-color: #409eff; box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.15); }
.edge-hdr { display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 12px; }
.sub-code { font-size: 12px; color: #909399; margin-top: 2px; }
.edge-metrics { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; background: #f8fafc; padding: 10px; border-radius: 6px; margin-bottom: 10px; }
.edge-metrics .lbl { display: block; font-size: 11px; color: #909399; }
.edge-foot { display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #606266; }
.canvas-box { background: #0b1220; border-radius: 8px; overflow: hidden; text-align: center; }
.roi-canvas { width: 100%; max-height: 430px; cursor: crosshair; display: block; }
.roi-hint { font-size: 12px; color: #606266; margin-top: 8px; }
.sha-box { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 10px; font-size: 12px; }
.sha-line { margin-top: 6px; word-break: break-all; color: #475569; }
.text-primary { color: #409eff; }
.text-success { color: #67c23a; }
.text-warning { color: #e6a23c; }
</style>
