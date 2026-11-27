<template>
  <div class="app-container">
    <el-row :gutter="16">
      <!-- 左侧：重大危险源档案导航列 -->
      <el-col :xs="24" :md="8">
        <el-card shadow="never">
          <template #header>
            <div class="hdr-flex">
              <span>重大危险源名录 ({{ profiles.length }})</span>
              <el-button type="primary" size="small" plain icon="Plus" @click="addOpen = true">新增档案</el-button>
            </div>
          </template>
          <div
            v-for="item in profiles"
            :key="item.hazardId"
            :class="['hz-item-card', selectedId === item.hazardId ? 'is-active' : '']"
            @click="selectHazard(item.hazardId)"
          >
            <div class="hz-card-top">
              <strong>{{ item.hazardName }}</strong>
              <el-tag size="small" :type="item.riskLevel === '重大风险' ? 'danger' : 'warning'">{{ item.riskLevel }}</el-tag>
            </div>
            <div class="hz-card-sub">
              <span>{{ item.deptName || '作业区' }} · {{ item.chemicalName }}</span>
              <span>R={{ item.rIndex }} ({{ item.majorHazardGrade }})</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <!-- 右侧：全息图谱拓扑穿透详情 -->
      <el-col :xs="24" :md="16">
        <el-card v-loading="loadingGraph" shadow="never">
          <template #header>
            <div class="hdr-flex">
              <span>「场所 ➔ 危险源 ➔ 特种设备 ➔ 监控球机 ➔ 人员 ➔ 应急预案」全息图谱</span>
              <el-button
                v-if="graph.hazard"
                type="danger"
                size="small"
                icon="Aim"
                @click="router.push(`/hazard-emergency/drill?hazardId=${graph.hazard.hazardId}`)"
              >
                对此危险源发起事故情景推演
              </el-button>
            </div>
          </template>

          <el-empty v-if="!graph.hazard" description="请选择左侧危险源查看全息关联图谱" />
          <div v-else>
            <!-- 六维关系拓扑链 -->
            <div class="topo-chain mb16">
              <div class="topo-node place">
                <div class="node-cap">所属场所/区域</div>
                <div class="node-val">{{ graph.hazard.deptName }}</div>
              </div>
              <div class="topo-arrow">➔</div>
              <div class="topo-node hazard">
                <div class="node-cap">核心危险源 ({{ graph.hazard.majorHazardGrade }})</div>
                <div class="node-val">{{ graph.hazard.chemicalName }} ({{ graph.hazard.actualQtyTon }}t)</div>
              </div>
              <div class="topo-arrow">➔</div>
              <div class="topo-node equip">
                <div class="node-cap">关联安全设备</div>
                <div class="node-val">{{ (graph.equipments || []).length }} 台/套联锁设施</div>
              </div>
              <div class="topo-arrow">➔</div>
              <div class="topo-node cam">
                <div class="node-cap">绑定视觉点位</div>
                <div class="node-val">{{ (graph.cameras || []).length }} 路防爆摄像机</div>
              </div>
              <div class="topo-arrow">➔</div>
              <div class="topo-node staff">
                <div class="node-cap">当班人数 / 负责人</div>
                <div class="node-val">{{ graph.hazard.onDutyCount }}人 / {{ graph.hazard.leader || '安全员' }}</div>
              </div>
            </div>

            <!-- 理化与应急参数描述 -->
            <el-descriptions :column="2" border size="small" class="mb16">
              <el-descriptions-item label="危险源编码">{{ graph.hazard.hazardCode }}</el-descriptions-item>
              <el-descriptions-item label="CAS号 / 临界量">{{ graph.hazard.casNo }} / 临界量 {{ graph.hazard.criticalQtyTon }} t</el-descriptions-item>
              <el-descriptions-item label="道氏MF / 燃烧热">MF={{ graph.hazard.dowMf }} / Qf={{ graph.hazard.combustionHeatKj }} kJ/kg</el-descriptions-item>
              <el-descriptions-item label="厂区平面坐标">X={{ graph.hazard.mapX }}%, Y={{ graph.hazard.mapY }}%</el-descriptions-item>
              <el-descriptions-item label="理化危险特性" :span="2">{{ graph.hazard.physicochemicalProps }}</el-descriptions-item>
              <el-descriptions-item label="初期应急处置要点" :span="2">{{ graph.hazard.emergencyMeasures }}</el-descriptions-item>
              <el-descriptions-item label="强制个体防护(PPE)" :span="2">{{ graph.hazard.ppeRequirements }}</el-descriptions-item>
            </el-descriptions>

            <!-- 关联特种设备与历史隐患双栏 -->
            <el-row :gutter="12">
              <el-col :span="12">
                <div class="sub-sec-title">关联特种与安全联锁设备</div>
                <el-table :data="graph.equipments" size="small" border>
                  <el-table-column prop="postCode" label="型号编码" width="120" />
                  <el-table-column prop="postName" label="设备名称" />
                </el-table>
              </el-col>
              <el-col :span="12">
                <div class="sub-sec-title">属地关联隐患排查工单</div>
                <el-table :data="graph.orders" size="small" border>
                  <el-table-column prop="hazardTitle" label="隐患摘要" show-overflow-tooltip />
                  <el-table-column prop="status" label="状态" width="90" align="center" />
                </el-table>
              </el-col>
            </el-row>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 新增危险源档案弹窗 -->
    <el-dialog v-model="addOpen" title="新增重大危险源全息档案" width="580px" append-to-body>
      <el-form :model="newForm" label-width="125px">
        <el-form-item label="危险源名称"><el-input v-model="newForm.hazardName" placeholder="例如：液氨制冷储罐单元" /></el-form-item>
        <el-form-item label="危险介质名称"><el-input v-model="newForm.chemicalName" placeholder="例如：液氨 (NH3)" /></el-form-item>
        <el-form-item label="所属场所">
          <el-select v-model="newForm.placeType" style="width: 100%">
            <el-option label="生产场所" value="production" />
            <el-option label="储存场所" value="storage" />
            <el-option label="公辅场所" value="auxiliary" />
          </el-select>
        </el-form-item>
        <el-form-item label="存量(t)/临界量(t)">
          <el-input-number v-model="newForm.actualQtyTon" :min="0" style="width: 48%; margin-right: 4%" />
          <el-input-number v-model="newForm.criticalQtyTon" :min="1" style="width: 48%" />
        </el-form-item>
        <el-form-item label="理化特性描述"><el-input v-model="newForm.physicochemicalProps" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="应急处置措施"><el-input v-model="newForm.emergencyMeasures" type="textarea" :rows="2" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addOpen = false">取消</el-button>
        <el-button type="primary" @click="saveNewHazard">保存入库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="HazardHologram">
import { ElMessage } from 'element-plus'
import { listHazardProfiles, getHazardGraph, addHazardProfile } from '@/api/ehs'

const route = useRoute()
const router = useRouter()
const profiles = ref([])
const selectedId = ref(null)
const loadingGraph = ref(false)
const graph = reactive({ hazard: null, equipments: [], cameras: [], orders: [], drills: [], laws: [] })

const addOpen = ref(false)
const newForm = reactive({
  hazardName: '',
  chemicalName: '',
  placeType: 'storage',
  deptId: 108,
  actualQtyTon: 20,
  criticalQtyTon: 10,
  rIndex: 4.0,
  majorHazardGrade: '四级重大危险源',
  riskLevel: '重大风险',
  physicochemicalProps: '',
  emergencyMeasures: ''
})

function loadList() {
  listHazardProfiles().then(res => {
    profiles.value = res.data || []
    const qId = route.query.hazardId ? Number(route.query.hazardId) : null
    const initId = qId || (profiles.value[0] && profiles.value[0].hazardId)
    if (initId) selectHazard(initId)
  })
}

function selectHazard(id) {
  selectedId.value = id
  loadingGraph.value = true
  getHazardGraph(id)
    .then(res => {
      if (res && res.data) Object.assign(graph, res.data)
    })
    .finally(() => {
      loadingGraph.value = false
    })
}

function saveNewHazard() {
  if (!newForm.hazardName.trim()) {
    ElMessage.warning('请填写危险源名称')
    return
  }
  const ratio = Number(newForm.actualQtyTon) / Math.max(1, Number(newForm.criticalQtyTon))
  newForm.rIndex = Number((ratio * 1.5).toFixed(2))
  newForm.majorHazardGrade = ratio >= 1 ? '四级重大危险源' : '非重大危险源'
  addHazardProfile(newForm).then(res => {
    ElMessage.success('危险源档案创建成功')
    addOpen.value = false
    loadList()
  })
}

onMounted(() => {
  loadList()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.hdr-flex { display: flex; justify-content: space-between; align-items: center; font-weight: 600; }
.hz-item-card {
  padding: 12px;
  margin-bottom: 10px;
  border-radius: 6px;
  border: 1px solid #ebeef5;
  cursor: pointer;
  transition: all 0.15s;
}
.hz-item-card.is-active, .hz-item-card:hover {
  border-color: #409eff;
  background: #ecf5ff;
}
.hz-card-top { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; font-size: 14px; }
.hz-card-sub { display: flex; justify-content: space-between; font-size: 12px; color: #606266; }
.topo-chain {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  padding: 12px;
  background: #f8f9fc;
  border-radius: 8px;
}
.topo-node {
  flex: 1;
  min-width: 110px;
  padding: 8px 10px;
  border-radius: 6px;
  background: #fff;
  border-left: 4px solid #409eff;
  box-shadow: 0 1px 4px rgba(0,0,0,0.05);
}
.topo-node.hazard { border-left-color: #f56c6c; }
.topo-node.equip { border-left-color: #e6a23c; }
.topo-node.cam { border-left-color: #67c23a; }
.node-cap { font-size: 11px; color: #909399; }
.node-val { font-size: 13px; font-weight: 600; color: #303133; margin-top: 3px; }
.topo-arrow { color: #909399; font-weight: bold; }
.sub-sec-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: #303133; }
</style>
