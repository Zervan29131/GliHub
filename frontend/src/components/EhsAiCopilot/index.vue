<template>
  <div>
    <!-- 全局右下角悬浮呼出按钮 -->
    <div class="ehs-copilot-fab" @click="drawerVisible = true" title="呼出 GliHub 安全合规助手">
      <el-icon :size="20"><ChatDotRound /></el-icon>
      <span class="fab-label">合规助手</span>
    </div>

    <!-- SSE 流式法规问答抽屉 -->
    <el-drawer
      v-model="drawerVisible"
      title="GliHub 安全合规助手（EHS 法规 RAG 流式问答）"
      size="440px"
      append-to-body
    >
      <div class="copilot-body">
        <div class="quick-prompts">
          <div class="prompt-hint">快捷法规溯源提问：</div>
          <el-tag
            v-for="q in presetQuestions"
            :key="q"
            size="small"
            effect="plain"
            class="prompt-chip"
            @click="sendPrompt(q)"
          >
            {{ q }}
          </el-tag>
        </div>

        <div ref="chatScrollRef" class="chat-messages">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            :class="['chat-bubble-row', msg.role === 'user' ? 'is-user' : 'is-assistant']"
          >
            <div class="bubble-card">
              <div class="bubble-role">{{ msg.role === 'user' ? '安全工程师' : 'GliHub 合规引擎' }}</div>
              <div class="bubble-content">{{ msg.content || (streaming && idx === messages.length - 1 ? '正在检索法规切片并推演...' : '') }}</div>
              <div v-if="msg.citations && msg.citations.length" class="citation-box">
                <div class="citation-title">权威法规标准出处引用：</div>
                <div v-for="c in msg.citations" :key="c.chunk_id" class="citation-item">
                  <el-tag size="small" type="warning">{{ c.doc_title }} {{ c.clause_no }}</el-tag>
                  <div class="citation-snippet">{{ c.chunk_text }}</div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="chat-input-bar">
          <el-input
            v-model="inputQuestion"
            placeholder="输入安全法规、GB国标、特殊作业或隐患定级问题..."
            clearable
            :disabled="streaming"
            @keyup.enter="sendPrompt()"
          >
            <template #append>
              <el-button type="primary" :loading="streaming" @click="sendPrompt()">发送</el-button>
            </template>
          </el-input>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<script setup name="EhsAiCopilot">
import { ElNotification } from 'element-plus'
import { getToken } from '@/utils/auth'

const route = useRoute()
const drawerVisible = ref(false)
const streaming = ref(false)
const inputQuestion = ref('')
const chatScrollRef = ref(null)
let wsInstance = null
let reconnectTimer = null

const presetQuestions = [
  '作业人员未佩戴安全帽违反《安全生产法》哪一条？',
  '甲醇与一氧化碳构成重大危险源的临界量是多少？',
  '特级动火与受限空间作业气体分析有哪些强制要求？',
  '危化品专用仓库双人双锁规定出自哪部法规？'
]

const messages = ref([
  {
    role: 'assistant',
    content: '您好！我是 GliHub 企业级安全合规助手。已连接安全生产法律法规与 GB 18218 / GB 30871 向量知识库，可随时为您提供带精准法条出处的合规解答。',
    citations: []
  }
])

function scrollToBottom() {
  nextTick(() => {
    if (chatScrollRef.value) {
      chatScrollRef.value.scrollTop = chatScrollRef.value.scrollHeight
    }
  })
}

async function sendPrompt(presetText) {
  const text = (presetText || inputQuestion.value || '').trim()
  if (!text || streaming.value) return
  inputQuestion.value = ''

  messages.value.push({ role: 'user', content: text })
  const assistantMsg = reactive({ role: 'assistant', content: '', citations: [] })
  messages.value.push(assistantMsg)
  streaming.value = true
  scrollToBottom()

  const baseApi = import.meta.env.VITE_APP_BASE_API || '/dev-api'
  const historyPayload = messages.value
    .slice(0, -1)
    .map(m => ({ role: m.role, content: m.content }))

  try {
    const resp = await fetch(`${baseApi}/ehs/kb/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        Authorization: 'Bearer ' + getToken()
      },
      body: JSON.stringify({
        messages: historyPayload,
        context_summary: `当前访问路由: ${route.path} (${route.meta?.title || '安全管理页面'})`
      })
    })
    if (!resp.ok || !resp.body) {
      assistantMsg.content = '请求合规问答接口异常，请确认登录状态有效。'
      streaming.value = false
      return
    }
    const reader = resp.body.getReader()
    const decoder = new TextDecoder('utf-8')
    let buffer = ''

    while (true) {
      const { value, done } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const rawLine of lines) {
        const ln = rawLine.trim()
        if (!ln.startsWith('data:')) continue
        const dataPart = ln.slice(5).trim()
        if (!dataPart || dataPart === '[DONE]') continue
        try {
          const obj = JSON.parse(dataPart)
          if (obj.type === 'citations' && Array.isArray(obj.citations)) {
            assistantMsg.citations = obj.citations
          } else if (obj.type === 'delta' && obj.delta) {
            assistantMsg.content += obj.delta
          }
          scrollToBottom()
        } catch (_) {}
      }
    }
  } catch (err) {
    assistantMsg.content = '网络流中断：' + (err.message || '未知错误')
  } finally {
    streaming.value = false
    scrollToBottom()
  }
}

function connectAlertWebSocket() {
  if (!getToken()) return
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  const baseApi = import.meta.env.VITE_APP_BASE_API || '/dev-api'
  const wsUrl = `${proto}//${window.location.host}${baseApi}/ws/alerts`
  try {
    wsInstance = new WebSocket(wsUrl)
    wsInstance.onmessage = (evt) => {
      try {
        const msg = JSON.parse(evt.data)
        if (msg.event === 'VISION_ALERT' && msg.data) {
          const a = msg.data
          ElNotification({
            title: `【AI视觉告警】${a.violationType || '现场违章'}`,
            message: `${a.deptName || '作业区'}（严重度：${a.severity}）— ${a.vlmDescription || '请前往视觉工作台或隐患工单核查'}`,
            type: a.severity === 'CRITICAL' || a.severity === 'HIGH' ? 'error' : 'warning',
            duration: 7000
          })
        }
      } catch (_) {}
    }
    wsInstance.onclose = () => {
      reconnectTimer = setTimeout(connectAlertWebSocket, 10000)
    }
  } catch (_) {}
}

onMounted(() => {
  connectAlertWebSocket()
})

onBeforeUnmount(() => {
  if (reconnectTimer) clearTimeout(reconnectTimer)
  if (wsInstance) wsInstance.close()
})
</script>

<style scoped>
.ehs-copilot-fab {
  position: fixed;
  right: 24px;
  bottom: 28px;
  z-index: 2001;
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 10px 16px;
  border-radius: 24px;
  background: linear-gradient(135deg, #0f4c81 0%, #1d70b8 100%);
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  box-shadow: 0 6px 18px rgba(15, 76, 129, 0.38);
  transition: transform 0.2s ease;
}
.ehs-copilot-fab:hover {
  transform: translateY(-2px);
}
.copilot-body {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 95px);
}
.quick-prompts {
  padding-bottom: 10px;
  border-bottom: 1px solid #ebeef5;
}
.prompt-hint {
  font-size: 12px;
  color: #909399;
  margin-bottom: 6px;
}
.prompt-chip {
  margin: 0 6px 6px 0;
  cursor: pointer;
}
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 12px 4px;
}
.chat-bubble-row {
  display: flex;
  margin-bottom: 14px;
}
.chat-bubble-row.is-user {
  justify-content: flex-end;
}
.bubble-card {
  max-width: 90%;
  padding: 10px 14px;
  border-radius: 10px;
  background: #f4f6f9;
  color: #303133;
  font-size: 13px;
  line-height: 1.65;
  white-space: pre-wrap;
}
.is-user .bubble-card {
  background: #e8f3ff;
  color: #103a63;
}
.bubble-role {
  font-size: 11px;
  font-weight: 600;
  color: #909399;
  margin-bottom: 4px;
}
.citation-box {
  margin-top: 10px;
  padding-top: 8px;
  border-top: 1px dashed #dcdfe6;
}
.citation-title {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
  margin-bottom: 6px;
}
.citation-item {
  margin-bottom: 6px;
}
.citation-snippet {
  font-size: 12px;
  color: #606266;
  margin-top: 3px;
}
.chat-input-bar {
  padding-top: 10px;
  border-top: 1px solid #ebeef5;
}
</style>
