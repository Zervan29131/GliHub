<template>
  <div class="app-container">
    <el-row :gutter="16" class="mb16">
      <!-- 事故情景参数设定 -->
      <el-col :xs="24" :lg="9">
        <el-card shadow="never">
          <template #header>
            <span style="font-weight: 600">事故情景推演参数配置</span>
          </template>
          <el-form :model="simForm" label-width="125px">
            <el-form-item label="触发危险源单元">
              <el-select v-model="simForm.hazardId" style="width: 100%">
                <el-option
                  v-for="h in hazards"
                  :key="h.hazardId"
                  :label="`${h.hazardName} (${h.deptName})`"
                  :value="h.hazardId"
                />
              </el-select>
            </el-form-item>
            <el-form-item label="模拟事故类型">
              <el-select v-model="simForm.accidentType" style="width: 100%">
                <el-option label="可燃气体/蒸气云爆炸与中毒" value="可燃气体/蒸气云爆炸与中毒" />
                <el-option label="储罐区池火与流淌火蔓延" value="储罐区池火与流淌火蔓延" />
                <el-option label="高压管线破裂喷射火" value="高压管线破裂喷射火" />
              </el-select>
            </el-form-item>
            <el-form-item label="预估泄漏量 (kg)">
              <el-input-number v-model="simForm.leakMassKg" :min="50" :max="500000" :step="500" style="width: 100%" />
            </el-form-item>
            <el-form-item label="实时主导风向">
              <el-select v-model="simForm.windDirection" style="width: 100%">
                <el-option label="东南风" value="东南风" />
                <el-option label="东风" value="东风" />
                <el-option label="南风" value="南风" />
                <el-option label="西北风" value="西北风" />
                <el-option label="北风" value="北风" />
              </el-select>
            </el-form-item>
            <el-form-item label="实时风速 (m/s)">
              <el-input-number v-model="simForm.windSpeedMs" :min="0.5" :max="25" :step="0.5" :precision="1" style="width: 100%" />
            </el-form-item>
            <el-form-item>
              <el-button type="danger" icon="Aim" :loading="simulating" @click="runDrill">
                秒级推演并生成《应急处置行动卡》
              </el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧：生成的《现场应急处置行动卡》 -->
      <el-col :xs="24" :lg="15">
        <el-card shadow="never">
          <template #header>
            <div class="hdr-flex">
              <span>《现场应急处置行动卡》实时输出</span>
              <el-button v-if="activeDrill.actionCardMarkdown" size="small" type="primary" plain icon="Download" @click="exportActionCard">
                导出行动卡 (.doc)
              </el-button>
            </div>
          </template>
          <el-empty v-if="!activeDrill.actionCardMarkdown" description="设置左侧事故参数并点击推演，秒级联动危险源特性、TNT波及半径与在岗人数生成行动卡" />
          <div v-else>
            <el-row :gutter="10" class="mb12">
              <el-col :span="6"><el-tag type="danger">死亡半径 R1: {{ activeDrill.r1DeathM }} m</el-tag></el-col>
              <el-col :span="6"><el-tag type="warning">重伤半径 R2: {{ activeDrill.r2SeriousM }} m</el-tag></el-col>
              <el-col :span="6"><el-tag type="info">轻伤警戒 R3: {{ activeDrill.r3MinorM }} m</el-tag></el-col>
              <el-col :span="6"><el-tag type="danger" effect="dark">波及在岗: {{ activeDrill.affectedStaffCount }} 人</el-tag></el-col>
            </el-row>
            <pre class="card-md">{{ activeDrill.actionCardMarkdown }}</pre>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 历史应急推演归档表 -->
    <el-card shadow="never">
      <template #header>
        <span style="font-weight: 600">历史事故情景推演记录</span>
      </template>
      <el-table :data="drillHistory" border size="small">
        <el-table-column prop="drillNo" label="推演单号" width="175" />
        <el-table-column prop="hazardName" label="危险源单元" min-width="180" />
        <el-table-column prop="accidentType" label="模拟情景" width="180" />
        <el-table-column prop="leakMassKg" label="泄漏量(kg)" width="105" align="center" />
        <el-table-column prop="windDirection" label="风向" width="85" align="center" />
        <el-table-column prop="r3MinorM" label="轻伤警戒圈 R3(m)" width="135" align="center" />
        <el-table-column prop="affectedStaffCount" label="波及人数" width="90" align="center" />
        <el-table-column label="操作" width="110" align="center">
          <template #default="{ row }">
            <el-button link type="primary" @click="activeDrill = { ...row }">查看行动卡</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup name="EmergencyDrill">
import { ElMessage } from 'element-plus'
import { listHazardProfiles, simulateEmergency, listEmergencyDrills } from '@/api/ehs'

const route = useRoute()
const simulating = ref(false)
const hazards = ref([])
const drillHistory = ref([])
const activeDrill = ref({})

const simForm = reactive({
  hazardId: 1,
  accidentType: '可燃气体/蒸气云爆炸与中毒',
  leakMassKg: 3000,
  windDirection: '东南风',
  windSpeedMs: 3.2
})

function loadHistory() {
  listEmergencyDrills({ pageNum: 1, pageSize: 10 }).then(res => {
    drillHistory.value = res.rows || []
    if (!activeDrill.value.drillId && drillHistory.value.length) {
      activeDrill.value = { ...drillHistory.value[0] }
    }
  })
}

function runDrill() {
  simulating.value = true
  simulateEmergency(simForm)
    .then(res => {
      if (res && res.data) {
        activeDrill.value = res.data
        ElMessage.success('事故后果推演与《现场应急处置行动卡》生成完成')
        loadHistory()
      }
    })
    .finally(() => {
      simulating.value = false
    })
}

function exportActionCard() {
  const html = `<html><head><meta charset="utf-8"></head><body><pre style="font-family:SimSun,serif;white-space:pre-wrap;">${activeDrill.value.actionCardMarkdown}</pre></body></html>`
  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${activeDrill.value.drillNo || 'GliHub'}_现场应急处置行动卡.doc`
  a.click()
}

onMounted(() => {
  listHazardProfiles().then(res => {
    hazards.value = res.data || []
    if (route.query.hazardId) {
      simForm.hazardId = Number(route.query.hazardId)
    } else if (hazards.value.length) {
      simForm.hazardId = hazards.value[0].hazardId
    }
  })
  loadHistory()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mb12 { margin-bottom: 12px; }
.hdr-flex { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.card-md {
  max-height: 380px;
  overflow-y: auto;
  padding: 14px;
  background: #fff9f9;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.7;
}
</style>
