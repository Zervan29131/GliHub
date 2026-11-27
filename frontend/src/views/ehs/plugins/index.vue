<template>
  <div class="app-container">
    <!-- 硬件加速自探测与三档部署 Profile 切换栏 -->
    <el-card shadow="never" class="mb16 profile-banner">
      <div class="profile-row">
        <div>
          <div class="profile-title">
            GliHub 3.0 七层开源 AI 模型选装中心（Plugin Registry &amp; Low-Precision Manager）
          </div>
          <div class="profile-sub">
            探测芯片：<b>{{ hardware.chip_model || 'CPU' }}</b> ·
            加速层级：<el-tag size="small" effect="plain">{{ hardware.accelerator_tier || 'cpu' }}</el-tag> ·
            ONNX 后端：<code>{{ (hardware.available_ort_providers || []).join(', ') || 'CPUExecutionProvider' }}</code> ·
            线程上限：<b>{{ hardware.cpu_threads || 4 }} 核</b>
          </div>
        </div>
        <div class="profile-actions">
          <el-radio-group v-model="activeProfile" size="small" @change="onProfileSwitch">
            <el-radio-button value="cpu-int8">cpu-int8 (纯CPU低精度)</el-radio-button>
            <el-radio-button value="local-q4">local-q4 (本地4-bit离线)</el-radio-button>
            <el-radio-button value="gpu-pro">gpu-pro (独显全开)</el-radio-button>
          </el-radio-group>
          <el-button size="small" icon="Refresh" :loading="loading" @click="fetchPlugins">刷新状态</el-button>
        </div>
      </div>
    </el-card>

    <!-- 7 大选装插件卡片矩阵 -->
    <el-row :gutter="16" class="mb16">
      <el-col v-for="p in plugins" :key="p.plugin_id" :xs="24" :md="12" :lg="8" class="mb16">
        <el-card shadow="hover" class="plugin-card">
          <div class="p-top">
            <div>
              <span class="p-layer">{{ p.layer }}</span>
              <h4 class="p-name">{{ p.name }}</h4>
            </div>
            <el-switch
              v-model="p.enabled"
              :disabled="!p.installed || p.status === 'GPU_REQUIRED'"
              active-text="启用"
              @change="val => onTogglePlugin(p, val)"
            />
          </div>

          <p class="p-desc">{{ p.description }}</p>

          <div class="p-tags">
            <el-tag size="small" :type="statusTagType(p.status)" effect="dark">{{ p.status }}</el-tag>
            <el-tag size="small" type="info">精度: {{ (p.preferred_precision || 'int8').toUpperCase() }}</el-tag>
            <el-tag size="small" type="info">内存增量: ~{{ p.min_ram_mb }} MB</el-tag>
          </div>

          <div class="p-cmd">
            <span>按需选装命令：</span>
            <code>{{ p.install_command }}</code>
          </div>
          <div class="p-fallback">
            <b>未选装/停用兜底：</b>{{ p.fallback_behavior }}
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- YOLOE 开放词汇零样本专项排查工作台 -->
    <el-card shadow="never">
      <template #header>
        <div class="hdr-between">
          <span>Ultralytics YOLOE 开放词汇零样本专项排查体验台（无需重训即时检出新目标）</span>
          <el-tag type="success" size="small">mod-yoloe 驱动</el-tag>
        </div>
      </template>

      <el-row :gutter="16">
        <el-col :xs="24" :lg="10">
          <el-form label-position="top" size="small">
            <el-form-item label="输入自定义中文/英文安全排查提示词（回车或逗号分隔）">
              <el-select
                v-model="openVocabForm.prompts"
                multiple
                filterable
                allow-create
                default-first-option
                style="width: 100%"
              >
                <el-option label="未佩戴安全帽" value="未佩戴安全帽" />
                <el-option label="违规使用手机" value="违规使用手机" />
                <el-option label="未盖盖子的化学品桶" value="未盖盖子的化学品桶" />
                <el-option label="堵塞消防通道的杂物" value="堵塞消防通道的杂物" />
                <el-option label="厂区违停货车" value="厂区违停货车" />
              </el-select>
            </el-form-item>
            <el-form-item label="选择测试巡检画面">
              <el-select v-model="openVocabForm.sampleRelPath" style="width: 100%">
                <el-option v-for="s in samples" :key="s.relPath" :label="s.title" :value="s.relPath" />
              </el-select>
            </el-form-item>
            <el-button type="primary" :loading="runningOv" style="width: 100%" @click="handleRunOpenVocab">
              执行零样本开放词汇检测 + VLM 复核
            </el-button>
          </el-form>
        </el-col>

        <el-col :xs="24" :lg="14">
          <el-empty v-if="!ovResult" description="选择排查词并点击执行，即可零训练检出对应隐患并匹配安全生产法规条款" :image-size="80" />
          <div v-else class="ov-res">
            <el-image
              v-if="ovResult.vision?.annotated_image_url"
              :src="resolveUrl(ovResult.vision.annotated_image_url.replace('/outputs/', '/ai-outputs/'))"
              style="max-height: 240px; border-radius: 6px; margin-bottom: 10px"
              fit="contain"
            />
            <div>
              <el-tag size="small" type="danger" class="mr8">
                检出目标 {{ ovResult.vision?.detections?.length || 0 }} 处 ({{ ovResult.vision?.inference_ms }} ms)
              </el-tag>
              <span v-if="ovResult.vlm_review" style="font-size: 13px; color: #303133">
                {{ ovResult.vlm_review.description }}
              </span>
            </div>
          </div>
        </el-col>
      </el-row>
    </el-card>
  </div>
</template>

<script setup name="EhsAiPluginsCenter">
import { ElMessage } from 'element-plus'
import {
  listAiPlugins,
  listBuiltInSamples,
  resolveBackendAssetUrl,
  runOpenVocabDetect,
  switchPrecisionProfile,
  toggleAiPlugin
} from '@/api/ehs'

const loading = ref(false)
const runningOv = ref(false)
const activeProfile = ref('cpu-int8')
const hardware = ref({})
const plugins = ref([])
const samples = ref([])
const ovResult = ref(null)

const openVocabForm = reactive({
  prompts: ['未佩戴安全帽', '违规使用手机'],
  sampleRelPath: 'zidane.jpg'
})

function resolveUrl(u) {
  return resolveBackendAssetUrl(u)
}

function statusTagType(st) {
  if (st === 'ACTIVE') return 'success'
  if (st === 'DISABLED') return 'warning'
  if (st === 'GPU_REQUIRED') return 'danger'
  return 'info'
}

function fetchPlugins() {
  loading.value = true
  Promise.all([listAiPlugins(), listBuiltInSamples()])
    .then(([pRes, sRes]) => {
      const data = pRes.data || {}
      activeProfile.value = data.deploy_profile || 'cpu-int8'
      hardware.value = data.hardware || {}
      plugins.value = data.plugins || []
      samples.value = sRes.data || []
    })
    .finally(() => {
      loading.value = false
    })
}

function onTogglePlugin(plugin, enabledVal) {
  toggleAiPlugin(plugin.plugin_id, { enabled: enabledVal }).then(() => {
    ElMessage.success(`${plugin.name} 已${enabledVal ? '启用' : '停用释放内存'}`)
    fetchPlugins()
  })
}

function onProfileSwitch(profileVal) {
  switchPrecisionProfile({ deploy_profile: profileVal }).then(() => {
    ElMessage.success(`已切换系统推理档位至 ${profileVal}`)
    fetchPlugins()
  })
}

function handleRunOpenVocab() {
  runningOv.value = true
  runOpenVocabDetect({
    sampleRelPath: openVocabForm.sampleRelPath,
    prompts: openVocabForm.prompts,
    enable_vlm: true
  })
    .then(res => {
      ovResult.value = res.data
      ElMessage.success('开放词汇排查完成')
    })
    .finally(() => {
      runningOv.value = false
    })
}

onMounted(() => {
  fetchPlugins()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mr8 { margin-right: 8px; }
.hdr-between { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.profile-banner { background: linear-gradient(120deg, #f8fafc 0%, #eff6ff 100%); border-color: #dbeafe; }
.profile-row { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; }
.profile-title { font-size: 16px; font-weight: 700; color: #0f172a; }
.profile-sub { font-size: 12px; color: #475569; margin-top: 6px; }
.profile-actions { display: flex; gap: 10px; align-items: center; }
.plugin-card { height: 100%; display: flex; flex-direction: column; }
.p-top { display: flex; justify-content: space-between; align-items: flex-start; }
.p-layer { font-size: 11px; color: #2563eb; font-weight: 600; }
.p-name { margin: 4px 0 8px; font-size: 15px; color: #1e293b; }
.p-desc { font-size: 12px; color: #64748b; line-height: 1.5; min-height: 38px; margin: 0 0 10px; }
.p-tags { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
.p-cmd { background: #0f172a; color: #e2e8f0; padding: 6px 10px; border-radius: 6px; font-size: 12px; margin-bottom: 8px; }
.p-fallback { font-size: 12px; color: #64748b; line-height: 1.45; }
.ov-res { background: #f8fafc; border-radius: 8px; padding: 12px; border: 1px solid #e2e8f0; }
</style>
