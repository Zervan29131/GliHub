<template>
  <div class="app-container">
    <el-form :inline="true" :model="query" class="mb12">
      <el-form-item label="评价区域">
        <el-input v-model="query.areaName" placeholder="输入作业区名称搜索" clearable @keyup.enter="loadRecords" />
      </el-form-item>
      <el-form-item label="评价方法">
        <el-select v-model="query.evalMethod" placeholder="全部方法" clearable style="width: 160px">
          <el-option label="COMPREHENSIVE 综合报告" value="COMPREHENSIVE" />
          <el-option label="DOW 道氏指数法" value="DOW" />
          <el-option label="LEC 危险性分析" value="LEC" />
          <el-option label="TNT 爆炸后果模拟" value="TNT" />
        </el-select>
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="loadRecords">查询</el-button>
      </el-form-item>
    </el-form>

    <el-table v-loading="loading" :data="rows" border>
      <el-table-column prop="evalNo" label="归档编号" width="180" />
      <el-table-column prop="placeType" label="场所类别" width="110" align="center" />
      <el-table-column prop="areaName" label="评价作业区域" width="150" />
      <el-table-column prop="evalMethod" label="评价算法" width="140" align="center">
        <template #default="{ row }"><el-tag size="small">{{ row.evalMethod }}</el-tag></template>
      </el-table-column>
      <el-table-column prop="riskGrade" label="风险等级结论" width="160" align="center" />
      <el-table-column prop="dynamicAlertCount" label="关联告警数" width="105" align="center" />
      <el-table-column prop="openOrderCount" label="未闭环隐患" width="105" align="center" />
      <el-table-column prop="evaluator" label="评价人" width="120" align="center" />
      <el-table-column prop="createTime" label="归档时间" width="165" align="center" />
      <el-table-column label="操作" width="170" align="center" fixed="right">
        <template #default="{ row }">
          <el-button link type="primary" @click="viewRecord(row)">查看详情 / 导出</el-button>
        </template>
      </el-table-column>
    </el-table>

    <pagination
      v-show="total > 0"
      :total="total"
      v-model:page="query.pageNum"
      v-model:limit="query.pageSize"
      @pagination="loadRecords"
    />

    <el-dialog v-model="detailOpen" :title="`评价归档详情 — ${current.evalNo || ''}`" width="740px" append-to-body>
      <el-descriptions :column="2" border size="small" class="mb12">
        <el-descriptions-item label="评价区域">{{ current.areaName }}</el-descriptions-item>
        <el-descriptions-item label="评价算法">{{ current.evalMethod }}</el-descriptions-item>
        <el-descriptions-item label="风险结论">{{ current.riskGrade }}</el-descriptions-item>
        <el-descriptions-item label="评价人">{{ current.evaluator }}</el-descriptions-item>
      </el-descriptions>
      <pre class="report-view">{{ current.aiReportMarkdown || current.resultMetricsJson }}</pre>
      <template #footer>
        <el-button v-if="current.aiReportMarkdown" type="primary" icon="Download" @click="downloadDoc">
          导出 Word (.doc)
        </el-button>
        <el-button @click="detailOpen = false">关 闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EvalRecords">
import { listEvalRecords } from '@/api/ehs'

const loading = ref(false)
const total = ref(0)
const rows = ref([])
const detailOpen = ref(false)
const current = ref({})

const query = reactive({ pageNum: 1, pageSize: 10, areaName: '', evalMethod: '' })

function loadRecords() {
  loading.value = true
  listEvalRecords(query)
    .then(res => {
      rows.value = res.rows || []
      total.value = res.total || 0
    })
    .finally(() => {
      loading.value = false
    })
}

function viewRecord(row) {
  current.value = { ...row }
  detailOpen.value = true
}

function downloadDoc() {
  const html = `<html><head><meta charset="utf-8"></head><body><pre style="font-family:SimSun,serif;white-space:pre-wrap;">${current.value.aiReportMarkdown}</pre></body></html>`
  const blob = new Blob([html], { type: 'application/msword;charset=utf-8' })
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = `${current.value.evalNo}_安全评价报告.doc`
  a.click()
}

onMounted(() => {
  loadRecords()
})
</script>

<style scoped>
.mb12 { margin-bottom: 12px; }
.report-view {
  max-height: 420px;
  overflow-y: auto;
  padding: 12px;
  background: #f7f8fa;
  border-radius: 6px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.65;
}
</style>
