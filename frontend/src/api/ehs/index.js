import request from '@/utils/request'

// ==================== 1. 全域态势指挥舱 ====================
export function getCommandOverview() {
  return request({ url: '/ehs/dashboard/overview', method: 'get' })
}

// ==================== 2. 智能视觉监控与 VLM 复核 ====================
export function listVisionModels(params) {
  return request({ url: '/ehs/vision/models', method: 'get', params })
}

export function addVisionModel(data) {
  return request({ url: '/ehs/vision/models', method: 'post', data })
}

export function updateVisionModel(data) {
  return request({ url: '/ehs/vision/models', method: 'put', data })
}

export function delVisionModel(modelId) {
  return request({ url: `/ehs/vision/models/${modelId}`, method: 'delete' })
}

export function listCameraPoints(params) {
  return request({ url: '/ehs/vision/points', method: 'get', params })
}

export function listBuiltInSamples() {
  return request({ url: '/ehs/vision/samples', method: 'get' })
}

export function detectBySample(data) {
  return request({ url: '/ehs/vision/detect/sample', method: 'post', data, timeout: 45000 })
}

export function detectByUpload(formData) {
  return request({
    url: '/ehs/vision/detect/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 45000
  })
}

export function listVisionAlerts(params) {
  return request({ url: '/ehs/vision/alerts', method: 'get', params })
}

export function convertAlertToOrder(alertId) {
  return request({ url: `/ehs/vision/alerts/${alertId}/convert-order`, method: 'put' })
}

export function dismissVisionAlert(alertId) {
  return request({ url: `/ehs/vision/alerts/${alertId}/dismiss`, method: 'put' })
}

// ==================== 3. 隐患排查治理闭环工单 ====================
export function listHazardOrders(params) {
  return request({ url: '/ehs/order/list', method: 'get', params })
}

export function createHazardOrder(data) {
  return request({ url: '/ehs/order', method: 'post', data })
}

export function updateHazardOrder(data) {
  return request({ url: '/ehs/order', method: 'put', data })
}

export function deleteHazardOrders(orderIds) {
  return request({ url: `/ehs/order/${orderIds}`, method: 'delete' })
}

export function submitRectifyUpload(orderId, formData) {
  return request({
    url: `/ehs/order/${orderId}/rectify-upload`,
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 45000
  })
}

export function submitRectifySample(orderId, data) {
  return request({ url: `/ehs/order/${orderId}/rectify-sample`, method: 'post', data, timeout: 45000 })
}

// ==================== 4. AI 动态安全评价引擎 ====================
export function getDynamicRiskStatus(params) {
  return request({ url: '/ehs/evaluate/dynamic-status', method: 'get', params })
}

export function listEvalRecords(params) {
  return request({ url: '/ehs/evaluate/records', method: 'get', params })
}

export function saveEvalCalc(data) {
  return request({ url: '/ehs/evaluate/calc-and-save', method: 'post', data })
}

export function requestAiEvalAssist(data) {
  return request({ url: '/ehs/evaluate/ai-assist', method: 'post', data, timeout: 40000 })
}

export function generateAiEvalReport(data) {
  return request({ url: '/ehs/evaluate/ai-report', method: 'post', data, timeout: 50000 })
}

export function queryTntSpatialImpact(data) {
  return request({ url: '/ehs/evaluate/tnt-impact', method: 'post', data })
}

// ==================== 5. 全息危险源图谱与事故推演 ====================
export function listHazardProfiles(params) {
  return request({ url: '/ehs/hazard/profiles', method: 'get', params })
}

export function getHazardGraph(hazardId) {
  return request({ url: `/ehs/hazard/${hazardId}/graph`, method: 'get' })
}

export function addHazardProfile(data) {
  return request({ url: '/ehs/hazard', method: 'post', data })
}

export function updateHazardProfile(data) {
  return request({ url: '/ehs/hazard', method: 'put', data })
}

export function deleteHazardProfile(hazardId) {
  return request({ url: `/ehs/hazard/${hazardId}`, method: 'delete' })
}

export function simulateEmergency(data) {
  return request({ url: '/ehs/emergency/simulate', method: 'post', data, timeout: 45000 })
}

export function listEmergencyDrills(params) {
  return request({ url: '/ehs/emergency/drills', method: 'get', params })
}

// ==================== 6. EHS 法规向量知识库 ====================
export function listKbDocs(params) {
  return request({ url: '/ehs/kb/docs', method: 'get', params })
}

export function listKbDocChunks(docId) {
  return request({ url: `/ehs/kb/docs/${docId}/chunks`, method: 'get' })
}

export function ingestKbText(data) {
  return request({ url: '/ehs/kb/ingest', method: 'post', data, timeout: 45000 })
}

export function uploadKbFile(formData) {
  return request({
    url: '/ehs/kb/upload',
    method: 'post',
    data: formData,
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000
  })
}

export function deleteKbDoc(docId) {
  return request({ url: `/ehs/kb/docs/${docId}`, method: 'delete' })
}

export function recommendKbLaws(params) {
  return request({ url: '/ehs/kb/recommend', method: 'get', params })
}

export function resolveBackendAssetUrl(relPath) {
  if (!relPath) return ''
  if (relPath.startsWith('http://') || relPath.startsWith('https://')) return relPath
  const base = import.meta.env.VITE_APP_BASE_API || '/dev-api'
  return base + (relPath.startsWith('/') ? relPath : `/${relPath}`)
}
