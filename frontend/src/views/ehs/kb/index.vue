<template>
  <div class="app-container">
    <!-- 顶部语义检索测试与文档入库工具栏 -->
    <el-card shadow="never" class="mb16">
      <div class="kb-top-bar">
        <div style="display: flex; gap: 8px; flex: 1; max-width: 620px">
          <el-input
            v-model="searchQuery"
            placeholder="输入安全问题或隐患关键词测试 RAG 向量检索（如：安全帽、甲醇临界量、动火作业）"
            clearable
            @keyup.enter="runSemanticSearch"
          />
          <el-button type="primary" icon="Search" @click="runSemanticSearch">向量语义检索</el-button>
        </div>
        <div>
          <el-button type="success" icon="DocumentAdd" @click="ingestOpen = true">文本/条款智能切分入库</el-button>
          <el-upload
            style="display: inline-block; margin-left: 8px"
            :show-file-list="false"
            accept=".pdf,.txt,.md"
            :http-request="handleDocFileUpload"
          >
            <el-button type="warning" plain icon="Upload" :loading="uploading">上传 PDF/国标/SDS 解析入库</el-button>
          </el-upload>
        </div>
      </div>

      <!-- 语义检索命中面板 -->
      <div v-if="searchHits.length" class="hit-panel mt12">
        <div class="hit-title">检索命中权威条款 Top-{{ searchHits.length }}：</div>
        <div v-for="(h, i) in searchHits" :key="i" class="hit-row">
          <el-tag size="small" type="warning" class="mr8">
            {{ h.doc_title || h.docTitle }} {{ h.clause_no || h.clauseNo }}
          </el-tag>
          <span v-if="h.score" class="score-badge">相似度 {{ h.score }}</span>
          <div class="hit-text">{{ h.chunk_text || h.chunkText }}</div>
        </div>
      </div>
    </el-card>

    <!-- 主体：左侧源文档列表，右侧结构化条款切片预览 -->
    <el-row :gutter="16">
      <el-col :xs="24" :md="11">
        <el-card shadow="never">
          <template #header>
            <span style="font-weight: 600">EHS 法规、国标与危化品 SDS 源文档列表</span>
          </template>
          <el-table :data="docs" border size="small" highlight-current-row @row-click="selectDoc">
            <el-table-column prop="docTitle" label="文献名称" min-width="190" />
            <el-table-column prop="docCategory" label="类别" width="90" align="center" />
            <el-table-column prop="chunkCount" label="切片数" width="75" align="center" />
            <el-table-column label="操作" width="75" align="center">
              <template #default="{ row }">
                <el-button link type="danger" size="small" @click.stop="handleDelete(row.docId)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :xs="24" :md="13">
        <el-card shadow="never">
          <template #header>
            <span style="font-weight: 600">
              结构化条款切片与向量索引明细 {{ activeDoc ? `— ${activeDoc.docTitle}` : '' }}
            </span>
          </template>
          <el-empty v-if="!chunks.length" description="点击左侧任意法规文档查看自动切分的条款明细" />
          <el-table v-else :data="chunks" border size="small" max-height="460">
            <el-table-column prop="clauseNo" label="条款号" width="130" />
            <el-table-column prop="chunkText" label="条款原文内容" min-width="280" />
            <el-table-column prop="applicablePlaces" label="适用场所" width="140" />
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <!-- 文本智能切分入库弹窗 -->
    <el-dialog v-model="ingestOpen" title="安全法规 / 国标 / 危化品 SDS 文本切分向量化入库" width="620px" append-to-body>
      <el-form :model="ingestForm" label-width="110px">
        <el-form-item label="文献标题">
          <el-input v-model="ingestForm.docTitle" placeholder="例如：GB 15603-2022《危险化学品仓库储存通则》" />
        </el-form-item>
        <el-form-item label="文献分类">
          <el-select v-model="ingestForm.docCategory" style="width: 48%; margin-right: 4%">
            <el-option label="LAW 法律法规" value="LAW" />
            <el-option label="STANDARD 国家标准" value="STANDARD" />
            <el-option label="SDS 化学品安全说明书" value="SDS" />
            <el-option label="RULE 企业规章制度" value="RULE" />
          </el-select>
          <el-input v-model="ingestForm.standardCode" placeholder="标准号（如 GB 15603-2022）" style="width: 48%" />
        </el-form-item>
        <el-form-item label="条款正文">
          <el-input
            v-model="ingestForm.rawText"
            type="textarea"
            :rows="6"
            placeholder="粘贴包含「第X条」或「5.1 / 5.2」章节号的法规标准内容，后台将自动按条款切分并生成 1024 维向量索引"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="ingestOpen = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="submitTextIngest">切分并写入向量库</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup name="EhsVectorKb">
import { ElMessage, ElMessageBox } from 'element-plus'
import { listKbDocs, listKbDocChunks, ingestKbText, uploadKbFile, deleteKbDoc, recommendKbLaws } from '@/api/ehs'

const searchQuery = ref('未佩戴安全帽与个体防护规定')
const searchHits = ref([])
const docs = ref([])
const activeDoc = ref(null)
const chunks = ref([])
const uploading = ref(false)
const ingestOpen = ref(false)

const ingestForm = reactive({
  docTitle: '',
  docCategory: 'STANDARD',
  standardCode: '',
  rawText: ''
})

function loadDocs() {
  listKbDocs().then(res => {
    docs.value = res.data || []
    if (docs.value.length && !activeDoc.value) {
      selectDoc(docs.value[0])
    }
  })
}

function selectDoc(row) {
  activeDoc.value = row
  listKbDocChunks(row.docId).then(res => {
    chunks.value = res.data || []
  })
}

function runSemanticSearch() {
  if (!searchQuery.value.trim()) return
  recommendKbLaws({ query: searchQuery.value.trim(), topK: 4 }).then(res => {
    searchHits.value = res.data || []
  })
}

function submitTextIngest() {
  if (!ingestForm.docTitle.trim() || !ingestForm.rawText.trim()) {
    ElMessage.warning('请填写文献标题与正文内容')
    return
  }
  uploading.value = true
  ingestKbText(ingestForm)
    .then(res => {
      ElMessage.success(`入库完成，共切分 ${res.data?.chunk_count || 1} 条向量切片`)
      ingestOpen.value = false
      activeDoc.value = null
      loadDocs()
    })
    .finally(() => {
      uploading.value = false
    })
}

function handleDocFileUpload(options) {
  const fd = new FormData()
  fd.append('file', options.file)
  fd.append('docTitle', options.file.name)
  fd.append('docCategory', 'STANDARD')
  uploading.value = true
  uploadKbFile(fd)
    .then(res => {
      ElMessage.success(`文件解析入库成功，生成 ${res.data?.chunk_count || 0} 条法规切片`)
      activeDoc.value = null
      loadDocs()
    })
    .finally(() => {
      uploading.value = false
    })
}

function handleDelete(docId) {
  ElMessageBox.confirm('确认删除该文献及其全部向量切片吗？', '提示', { type: 'warning' })
    .then(() => deleteKbDoc(docId))
    .then(() => {
      ElMessage.success('删除成功')
      activeDoc.value = null
      chunks.value = []
      loadDocs()
    })
    .catch(() => {})
}

onMounted(() => {
  loadDocs()
  runSemanticSearch()
})
</script>

<style scoped>
.mb16 { margin-bottom: 16px; }
.mt12 { margin-top: 12px; }
.mr8 { margin-right: 8px; }
.kb-top-bar { display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; }
.hit-panel { padding: 12px; background: #f8fafc; border-radius: 6px; border: 1px solid #e4e7ed; }
.hit-title { font-size: 13px; font-weight: 600; margin-bottom: 8px; }
.hit-row { margin-bottom: 8px; }
.score-badge { font-size: 12px; color: #67c23a; font-weight: 600; }
.hit-text { font-size: 12px; color: #606266; margin-top: 4px; }
</style>
