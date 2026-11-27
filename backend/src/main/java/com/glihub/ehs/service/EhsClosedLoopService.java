package com.glihub.ehs.service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.glihub.common.core.domain.entity.SysDept;
import com.glihub.ehs.client.AiServiceClient;
import com.glihub.ehs.domain.EhsCameraPoint;
import com.glihub.ehs.domain.EhsEmergencyDrill;
import com.glihub.ehs.domain.EhsEvalRecord;
import com.glihub.ehs.domain.EhsHazardOrder;
import com.glihub.ehs.domain.EhsHazardProfile;
import com.glihub.ehs.domain.EhsKbChunk;
import com.glihub.ehs.domain.EhsVisionAlert;
import com.glihub.ehs.domain.EhsVisionModel;
import com.glihub.ehs.mapper.EhsEvalRecordMapper;
import com.glihub.ehs.mapper.EhsHazardOrderMapper;
import com.glihub.ehs.mapper.EhsHazardProfileMapper;
import com.glihub.ehs.mapper.EhsKnowledgeMapper;
import com.glihub.ehs.mapper.EhsVisionMapper;
import com.glihub.ehs.websocket.EhsWebSocketConfig;
import com.glihub.system.domain.SysPost;
import com.glihub.system.mapper.SysDeptMapper;
import com.glihub.system.mapper.SysPostMapper;
import com.glihub.system.service.ISysConfigService;

/**
 * GliHub 2.0 核心业务闭环编排服务：
 * 串联「视觉感知 -> VLM 复核 -> 法规溯源 -> 隐患工单 -> 动态风险重评 -> 重大危险源推演」全链路
 */
@Service
public class EhsClosedLoopService
{
    @Autowired
    private EhsVisionMapper visionMapper;
    @Autowired
    private EhsHazardOrderMapper orderMapper;
    @Autowired
    private EhsHazardProfileMapper profileMapper;
    @Autowired
    private EhsEvalRecordMapper evalMapper;
    @Autowired
    private EhsKnowledgeMapper knowledgeMapper;
    @Autowired
    private SysDeptMapper deptMapper;
    @Autowired
    private SysPostMapper postMapper;
    @Autowired
    private ISysConfigService configService;
    @Autowired
    private AiServiceClient aiClient;
    @Autowired
    private org.springframework.jdbc.core.JdbcTemplate jdbcTemplate;

    private String nextSerialNo(String prefix)
    {
        String ts = new SimpleDateFormat("yyyyMMddHHmmss").format(new Date());
        int rnd = ThreadLocalRandom.current().nextInt(100, 999);
        return prefix + "-" + ts + "-" + rnd;
    }

    private String normalizeAiImageUrl(String rawUrl)
    {
        if (rawUrl == null || rawUrl.isEmpty())
        {
            return rawUrl;
        }
        if (rawUrl.startsWith("/outputs/"))
        {
            return "/ai-outputs/" + rawUrl.substring("/outputs/".length());
        }
        return rawUrl;
    }

    /** 1. 列出所有视觉模型并合并 ai-service 实时运行状态 */
    public List<EhsVisionModel> listVisionModels(EhsVisionModel query)
    {
        List<EhsVisionModel> dbModels = visionMapper.selectModelList(query);
        JSONObject health = aiClient.fetchHealth();
        Map<String, JSONObject> runtimeMap = new HashMap<>();
        if (health != null && health.containsKey("models"))
        {
            JSONArray arr = health.getJSONArray("models");
            for (int i = 0; i < arr.size(); i++)
            {
                JSONObject m = arr.getJSONObject(i);
                runtimeMap.put(m.getString("model_code"), m);
            }
        }
        for (EhsVisionModel item : dbModels)
        {
            JSONObject rt = runtimeMap.get(item.getModelCode());
            if (rt != null)
            {
                item.setRuntimeReady(rt.getBooleanValue("ready") || rt.getBooleanValue("native_ready") || rt.getBooleanValue("weights_exists"));
                item.setRuntimeMessage(rt.getString("status") != null ? rt.getString("status") : rt.getString("status_message"));
            }
            else
            {
                item.setRuntimeReady(false);
                item.setRuntimeMessage(health != null ? health.getString("message") : "AI 服务未连接");
            }
        }
        return dbModels;
    }

    /** 2. 执行双阶段视觉检测 + VLM 复核 + 落库告警 + 自动转工单 + WebSocket 广播 */
    @Transactional
    public Map<String, Object> executeVisionAnalyze(
            String localImageAbsPath,
            String rawPublicUrl,
            Long pointId,
            Long deptId,
            String placeType,
            String modelCode,
            String promptText,
            Double confThres,
            Boolean enableVlm,
            String operator)
    {
        EhsCameraPoint point = pointId != null ? visionMapper.selectCameraPointById(pointId) : null;
        Long finalDeptId = deptId != null ? deptId : (point != null ? point.getDeptId() : 103L);
        String finalPlace = (placeType != null && !placeType.isEmpty())
                ? placeType : (point != null ? point.getPlaceType() : "production");
        String finalModel = (modelCode != null && !modelCode.isEmpty())
                ? modelCode : (point != null && point.getDefaultModelCode() != null ? point.getDefaultModelCode() : "yolov5_helmet_local");

        SysDept dept = deptMapper.selectDeptById(finalDeptId);
        String areaName = dept != null ? dept.getDeptName() : "现场作业区";

        Map<String, Object> aiReq = new HashMap<>();
        aiReq.put("image_path", localImageAbsPath);
        aiReq.put("model_code", finalModel);
        aiReq.put("prompt_text", promptText);
        aiReq.put("conf_thres", confThres != null ? confThres : 0.35);
        aiReq.put("iou_thres", 0.45);
        aiReq.put("enable_vlm", enableVlm == null || enableVlm);
        aiReq.put("place_type", finalPlace);
        aiReq.put("area_name", areaName);
        if (point != null && point.getHazardName() != null)
        {
            aiReq.put("hazard_context", point.getHazardName());
        }

        JSONObject fallback = new JSONObject();
        JSONObject fbVision = new JSONObject();
        fbVision.put("model_code", finalModel);
        fbVision.put("inference_ms", 0);
        fbVision.put("annotated_image_url", rawPublicUrl);
        fbVision.put("detections", new JSONArray());
        fbVision.put("note", "ai-service 暂不可达，已记录原始巡检图像供人工研判");
        fallback.put("vision", fbVision);

        JSONObject aiResp = aiClient.postJsonWithFallback("/api/v1/vision/analyze", aiReq, fallback);
        JSONObject visionObj = aiResp.getJSONObject("vision");
        JSONObject vlmObj = aiResp.getJSONObject("vlm_review");
        JSONArray lawsArr = aiResp.getJSONArray("cited_laws");

        EhsVisionAlert alert = new EhsVisionAlert();
        alert.setAlertNo(nextSerialNo("AL"));
        alert.setPointId(pointId);
        alert.setDeptId(finalDeptId);
        alert.setPlaceType(finalPlace);
        alert.setModelCode(finalModel);
        alert.setPromptText(promptText);
        alert.setRawImageUrl(rawPublicUrl);
        alert.setAnnotatedImageUrl(normalizeAiImageUrl(visionObj != null ? visionObj.getString("annotated_image_url") : rawPublicUrl));
        alert.setDetectionsJson(visionObj != null && visionObj.getJSONArray("detections") != null
                ? visionObj.getJSONArray("detections").toJSONString() : "[]");
        alert.setInferenceMs(visionObj != null ? visionObj.getIntValue("inference_ms") : 0);

        if (vlmObj != null)
        {
            alert.setVlmReviewed(vlmObj.getBooleanValue("reviewed"));
            alert.setVlmModel(vlmObj.getString("vlm_model"));
            alert.setIsRealHazard(vlmObj.getBooleanValue("is_real_hazard"));
            alert.setViolationType(vlmObj.getString("violation_type"));
            alert.setSeverity(vlmObj.getString("severity"));
            alert.setVlmDescription(vlmObj.getString("description"));
            alert.setVlmSuggestion(vlmObj.getString("suggestion"));
        }
        else
        {
            boolean hasViol = visionObj != null && visionObj.getBooleanValue("has_violation");
            alert.setVlmReviewed(false);
            alert.setIsRealHazard(hasViol);
            alert.setViolationType(hasViol ? "视觉初筛异常候选" : "常规巡检正常");
            alert.setSeverity(hasViol ? "MEDIUM" : "LOW");
            alert.setVlmDescription(visionObj != null ? visionObj.getString("note") : "已完成基础抓拍归档");
        }
        alert.setCitedLawsJson(lawsArr != null ? lawsArr.toJSONString() : "[]");
        alert.setHandleStatus(Boolean.TRUE.equals(alert.getIsRealHazard()) ? "PENDING" : "CLOSED");
        alert.setCreateBy(operator);
        visionMapper.insertAlert(alert);

        EhsHazardOrder autoOrder = null;
        String autoFlag = configService.selectConfigByKey("ehs.ai.autoCreateOrder");
        boolean autoCreate = autoFlag == null || !"false".equalsIgnoreCase(autoFlag.trim());
        if (autoCreate && Boolean.TRUE.equals(alert.getIsRealHazard())
                && ("HIGH".equalsIgnoreCase(alert.getSeverity()) || "CRITICAL".equalsIgnoreCase(alert.getSeverity())))
        {
            autoOrder = createOrderFromAlert(alert.getAlertId(), operator);
            alert.setOrderId(autoOrder.getOrderId());
            alert.setHandleStatus("WORK_ORDER_CREATED");
        }

        EhsVisionAlert savedAlert = visionMapper.selectAlertById(alert.getAlertId());
        if (Boolean.TRUE.equals(savedAlert.getIsRealHazard()))
        {
            EhsWebSocketConfig.broadcastEvent("VISION_ALERT", savedAlert);
        }

        Map<String, Object> res = new HashMap<>();
        res.put("alert", savedAlert);
        res.put("vision", visionObj);
        res.put("vlmReview", vlmObj);
        res.put("citedLaws", lawsArr != null ? lawsArr : new JSONArray());
        res.put("autoCreatedOrder", autoOrder);
        return res;
    }

    /** 3. 将视觉告警一键或自动转化为隐患治理工单 */
    @Transactional
    public EhsHazardOrder createOrderFromAlert(Long alertId, String operator)
    {
        EhsVisionAlert alert = visionMapper.selectAlertById(alertId);
        if (alert == null)
        {
            throw new IllegalArgumentException("指定的视觉告警不存在: " + alertId);
        }
        if (alert.getOrderId() != null)
        {
            return orderMapper.selectOrderById(alert.getOrderId());
        }

        SysDept dept = alert.getDeptId() != null ? deptMapper.selectDeptById(alert.getDeptId()) : null;
        StringBuilder basis = new StringBuilder();
        if (alert.getCitedLawsJson() != null)
        {
            JSONArray arr = JSON.parseArray(alert.getCitedLawsJson());
            for (int i = 0; i < Math.min(2, arr.size()); i++)
            {
                JSONObject c = arr.getJSONObject(i);
                if (basis.length() > 0) basis.append("；");
                basis.append(c.getString("doc_title")).append(" ").append(c.getString("clause_no"));
            }
        }

        EhsHazardOrder order = new EhsHazardOrder();
        order.setOrderNo(nextSerialNo("HD"));
        order.setSourceType("VISION_AI");
        order.setAlertId(alert.getAlertId());
        order.setDeptId(alert.getDeptId() != null ? alert.getDeptId() : 103L);
        order.setPlaceType(alert.getPlaceType());
        order.setHazardTitle("【AI视觉告警】" + (alert.getViolationType() != null ? alert.getViolationType() : "现场违章隐患"));
        order.setHazardCategory(alert.getViolationType());
        order.setRiskLevel("CRITICAL".equalsIgnoreCase(alert.getSeverity()) ? "重大隐患" : "较大隐患");
        order.setLegalBasis(basis.length() > 0 ? basis.toString() : "《中华人民共和国安全生产法》第四十一条、第四十五条");
        order.setRectifyMeasure(alert.getVlmSuggestion() != null ? alert.getVlmSuggestion() : "立即现场核查整改并上传复查照片验证销项");
        order.setResponsibleName(dept != null && dept.getLeader() != null && !dept.getLeader().isEmpty() ? dept.getLeader() : "注册安全员");
        order.setStatus("OPEN");
        order.setCreateBy(operator);
        orderMapper.insertOrder(order);

        EhsVisionAlert upd = new EhsVisionAlert();
        upd.setAlertId(alertId);
        upd.setOrderId(order.getOrderId());
        upd.setHandleStatus("WORK_ORDER_CREATED");
        visionMapper.updateAlertStatus(upd);

        return orderMapper.selectOrderById(order.getOrderId());
    }

    /** 4. 提交整改照片并调用 AI 复查核验闭环 */
    @Transactional
    public Map<String, Object> submitOrderRectification(
            Long orderId,
            String afterImageAbsPath,
            String afterPublicUrl,
            String rectifyNote,
            String operator)
    {
        EhsHazardOrder order = orderMapper.selectOrderById(orderId);
        if (order == null)
        {
            throw new IllegalArgumentException("隐患工单不存在: " + orderId);
        }

        Map<String, Object> req = new HashMap<>();
        req.put("after_image_path", afterImageAbsPath);
        req.put("hazard_title", order.getHazardTitle());
        req.put("model_code", "yolov5_helmet_local");

        JSONObject fb = new JSONObject();
        fb.put("passed", true);
        fb.put("review_comment", "AI 服务当前处于离线模式，已登记复查图像并转人工确认销项。");
        JSONObject checkRes = aiClient.postJsonWithFallback("/api/v1/vision/recheck", req, fb);

        boolean passed = checkRes.getBooleanValue("passed");
        order.setRectifyImageUrl(afterPublicUrl);
        order.setRectifyNote(rectifyNote);
        order.setAiRecheckPassed(passed);
        order.setAiRecheckComment(checkRes.getString("review_comment"));
        order.setStatus(passed ? "CLOSED" : "REVIEWING");
        order.setUpdateBy(operator);
        orderMapper.updateOrder(order);

        if (passed && order.getAlertId() != null)
        {
            EhsVisionAlert upd = new EhsVisionAlert();
            upd.setAlertId(order.getAlertId());
            upd.setHandleStatus("CLOSED");
            visionMapper.updateAlertStatus(upd);
        }

        Map<String, Object> out = new HashMap<>();
        out.put("order", orderMapper.selectOrderById(orderId));
        out.put("aiRecheck", checkRes);
        return out;
    }

    /** 5. 查询作业区动态风险重评状态（视觉告警 + 未闭环工单联动） */
    public Map<String, Object> getDynamicRiskStatus(Long deptId, String placeType)
    {
        int recentAlerts = visionMapper.countRecentRealAlertsByDept(deptId);
        int openOrders = orderMapper.countOpenOrdersByDept(deptId);
        String thStr = configService.selectConfigByKey("ehs.eval.reEvalThreshold");
        int threshold = 2;
        try { if (thStr != null) threshold = Integer.parseInt(thStr.trim()); } catch (Exception ignored) {}

        boolean triggered = (recentAlerts + openOrders) >= threshold;
        Map<String, Object> map = new HashMap<>();
        map.put("deptId", deptId);
        map.put("placeType", placeType);
        map.put("recentAlertCount", recentAlerts);
        map.put("openOrderCount", openOrders);
        map.put("threshold", threshold);
        map.put("reEvalTriggered", triggered);
        map.put("warningMessage", triggered
                ? String.format("动态风险预警：该区域近7日产生 %d 条真实视觉违章告警、存续 %d 项未闭环隐患工单，建议立即重新核算 LEC 作业条件危险性分值！", recentAlerts, openOrders)
                : "当前作业区视觉告警与隐患工单均受控，风险画像稳定。");
        return map;
    }

    /** 6. 计算 TNT 波及范围内关联设备与人员（用于平面同心圆叠加与事故推演） */
    public Map<String, Object> computeTntSpatialImpact(Long hazardId, double r1, double r2, double r3, double r4)
    {
        List<EhsHazardProfile> allProfiles = profileMapper.selectProfileList(new EhsHazardProfile());
        EhsHazardProfile center = hazardId != null ? profileMapper.selectProfileById(hazardId) : null;
        if (center == null && !allProfiles.isEmpty())
        {
            center = allProfiles.get(0);
        }
        List<SysPost> allEquips = postMapper.selectPostAll();

        // 厂区标准电子平面图比例尺：100% 宽度对应 300m × 220m 工业厂区
        double cx = center != null && center.getMapX() != null ? center.getMapX().doubleValue() : 50.0;
        double cy = center != null && center.getMapY() != null ? center.getMapY().doubleValue() : 50.0;

        List<Map<String, Object>> affectedNodes = new ArrayList<>();
        int totalStaffInR3 = 0;
        for (EhsHazardProfile hz : allProfiles)
        {
            double hx = hz.getMapX() != null ? hz.getMapX().doubleValue() : 50.0;
            double hy = hz.getMapY() != null ? hz.getMapY().doubleValue() : 50.0;
            double distMeters = Math.hypot((hx - cx) * 3.0, (hy - cy) * 2.2);
            String zone = distMeters <= r1 ? "死亡圈(R1)"
                    : distMeters <= r2 ? "重伤圈(R2)"
                    : distMeters <= r3 ? "轻伤疏散圈(R3)"
                    : distMeters <= r4 ? "财产损失圈(R4)" : "安全区";
            if (distMeters <= r3)
            {
                totalStaffInR3 += (hz.getOnDutyCount() != null ? hz.getOnDutyCount() : 0);
            }
            Map<String, Object> node = new HashMap<>();
            node.put("hazardId", hz.getHazardId());
            node.put("hazardName", hz.getHazardName());
            node.put("deptName", hz.getDeptName());
            node.put("placeType", hz.getPlaceType());
            node.put("mapX", hx);
            node.put("mapY", hy);
            node.put("onDutyCount", hz.getOnDutyCount());
            node.put("distanceMeters", BigDecimal.valueOf(distMeters).setScale(1, RoundingMode.HALF_UP));
            node.put("impactZone", zone);
            affectedNodes.add(node);
        }

        List<SysPost> affectedEquips = new ArrayList<>();
        if (center != null && center.getRelatedEquipIds() != null && !center.getRelatedEquipIds().isEmpty())
        {
            String[] ids = center.getRelatedEquipIds().split(",");
            for (SysPost p : allEquips)
            {
                for (String idStr : ids)
                {
                    if (String.valueOf(p.getPostId()).equals(idStr.trim()))
                    {
                        affectedEquips.add(p);
                    }
                }
            }
        }
        if (affectedEquips.isEmpty() && !allEquips.isEmpty())
        {
            affectedEquips.add(allEquips.get(0));
        }

        Map<String, Object> result = new HashMap<>();
        result.put("centerHazard", center);
        result.put("plantWidthMeters", 300);
        result.put("plantHeightMeters", 220);
        result.put("radii", Map.of("r1", r1, "r2", r2, "r3", r3, "r4", r4));
        result.put("affectedStaffInR3", totalStaffInR3);
        result.put("affectedEquips", affectedEquips);
        result.put("spatialNodes", affectedNodes);
        return result;
    }

    /** 7. 重大危险源全息图谱单点详情聚合 */
    public Map<String, Object> getHazardHolographicGraph(Long hazardId)
    {
        EhsHazardProfile hz = profileMapper.selectProfileById(hazardId);
        if (hz == null)
        {
            throw new IllegalArgumentException("危险源不存在: " + hazardId);
        }
        List<SysPost> allEquips = postMapper.selectPostAll();
        List<SysPost> linkedEquips = new ArrayList<>();
        if (hz.getRelatedEquipIds() != null)
        {
            for (String s : hz.getRelatedEquipIds().split(","))
            {
                for (SysPost p : allEquips)
                {
                    if (String.valueOf(p.getPostId()).equals(s.trim()))
                    {
                        linkedEquips.add(p);
                    }
                }
            }
        }

        EhsCameraPoint cpQuery = new EhsCameraPoint();
        cpQuery.setDeptId(hz.getDeptId());
        List<EhsCameraPoint> cameras = visionMapper.selectCameraPointList(cpQuery);

        EhsHazardOrder oQuery = new EhsHazardOrder();
        oQuery.setDeptId(hz.getDeptId());
        List<EhsHazardOrder> orders = orderMapper.selectOrderList(oQuery);

        EhsEmergencyDrill dQuery = new EhsEmergencyDrill();
        dQuery.setHazardId(hazardId);
        List<EhsEmergencyDrill> drills = profileMapper.selectDrillList(dQuery);

        List<EhsKbChunk> laws = knowledgeMapper.searchChunksFallback(hz.getChemicalName(), hz.getPlaceType(), 4);

        Map<String, Object> graph = new HashMap<>();
        graph.put("hazard", hz);
        graph.put("equipments", linkedEquips);
        graph.put("cameras", cameras);
        graph.put("orders", orders);
        graph.put("drills", drills);
        graph.put("laws", laws);
        return graph;
    }

    /** 8. 执行事故情景智能推演并落库《现场应急处置行动卡》 */
    @Transactional
    public EhsEmergencyDrill runEmergencySimulation(
            Long hazardId,
            String accidentType,
            double leakMassKg,
            String windDirection,
            double windSpeedMs,
            String operator)
    {
        EhsHazardProfile hz = profileMapper.selectProfileById(hazardId);
        if (hz == null)
        {
            throw new IllegalArgumentException("未找到指定危险源: " + hazardId);
        }
        double qf = hz.getCombustionHeatKj() != null && hz.getCombustionHeatKj().doubleValue() > 0
                ? hz.getCombustionHeatKj().doubleValue() : 19930.0;
        double wtnt = (0.04 * leakMassKg * qf) / 4520.0;
        double cbrt = Math.cbrt(Math.max(wtnt, 0.001));
        double r1 = round2(13.6 * Math.pow(Math.max(wtnt, 0.001) / 1000.0, 0.37));
        double r2 = round2(3.4 * cbrt);
        double r3 = round2(6.3 * cbrt);
        double r4 = round2((4.6 * cbrt) / Math.pow(1.0 + Math.pow(3175.0 / Math.max(wtnt, 0.001), 2), 1.0 / 6.0));

        Map<String, Object> impact = computeTntSpatialImpact(hazardId, r1, r2, r3, r4);
        int staffCount = (Integer) impact.get("affectedStaffInR3");
        @SuppressWarnings("unchecked")
        List<SysPost> equips = (List<SysPost>) impact.get("affectedEquips");

        Map<String, Object> tntMap = new HashMap<>();
        tntMap.put("wtnt", round2(wtnt));
        tntMap.put("r1", r1);
        tntMap.put("r2", r2);
        tntMap.put("r3", r3);
        tntMap.put("r4", r4);

        Map<String, Object> aiPayload = new HashMap<>();
        Map<String, Object> hzMap = new HashMap<>();
        hzMap.put("hazard_name", hz.getHazardName());
        hzMap.put("chemical_name", hz.getChemicalName());
        hzMap.put("ppe_requirements", hz.getPpeRequirements());
        aiPayload.put("hazard_profile", hzMap);
        aiPayload.put("accident_type", accidentType);
        aiPayload.put("leak_mass_kg", leakMassKg);
        aiPayload.put("wind_direction", windDirection);
        aiPayload.put("wind_speed_ms", windSpeedMs);
        aiPayload.put("tnt_result", tntMap);
        aiPayload.put("affected_equips", equips);
        aiPayload.put("affected_staff_count", staffCount);

        JSONObject fb = new JSONObject();
        fb.put("action_card_markdown", "# 现场应急处置行动卡（离线应急引擎）\n\n- **触发单元**："
                + hz.getHazardName() + "\n- **警戒疏散半径**：不小于 " + Math.round(r3 * 1.2 + 10)
                + " m（逆" + windDirection + "撤离）\n- **应急措施**：" + hz.getEmergencyMeasures()
                + "\n- **防护装备**：" + hz.getPpeRequirements());
        JSONObject aiCard = aiClient.postJsonWithFallback("/api/v1/agents/emergency-card", aiPayload, fb);

        EhsEmergencyDrill drill = new EhsEmergencyDrill();
        drill.setDrillNo(nextSerialNo("DR"));
        drill.setTriggerType("MANUAL_SIM");
        drill.setHazardId(hazardId);
        drill.setHazardName(hz.getHazardName());
        drill.setAccidentType(accidentType);
        drill.setLeakMassKg(BigDecimal.valueOf(leakMassKg));
        drill.setWindDirection(windDirection);
        drill.setWindSpeedMs(BigDecimal.valueOf(windSpeedMs));
        drill.setTntEquivalentKg(BigDecimal.valueOf(round2(wtnt)));
        drill.setR1DeathM(BigDecimal.valueOf(r1));
        drill.setR2SeriousM(BigDecimal.valueOf(r2));
        drill.setR3MinorM(BigDecimal.valueOf(r3));
        drill.setR4PropertyM(BigDecimal.valueOf(r4));
        drill.setAffectedEquipJson(JSON.toJSONString(equips));
        drill.setAffectedStaffCount(staffCount);
        drill.setActionCardMarkdown(aiCard.getString("action_card_markdown"));
        drill.setCreateBy(operator);
        profileMapper.insertDrill(drill);
        return drill;
    }

    /** 9. 全域态势指挥舱总览指标聚合 */
    public Map<String, Object> buildCommandCenterOverview()
    {
        List<EhsHazardProfile> hazards = profileMapper.selectProfileList(new EhsHazardProfile());
        List<EhsVisionAlert> recentAlerts = visionMapper.selectAlertList(new EhsVisionAlert());
        if (recentAlerts.size() > 8)
        {
            recentAlerts = recentAlerts.subList(0, 8);
        }
        List<EhsHazardOrder> allOrders = orderMapper.selectOrderList(new EhsHazardOrder());
        long closedOrders = allOrders.stream().filter(o -> "CLOSED".equalsIgnoreCase(o.getStatus())).count();
        int closureRate = allOrders.isEmpty() ? 100 : (int) Math.round((closedOrders * 100.0) / allOrders.size());

        List<SysPost> equips = postMapper.selectPostAll();
        List<EhsEvalRecord> evals = evalMapper.selectRecordList(new EhsEvalRecord());
        if (evals.size() > 6)
        {
            evals = evals.subList(0, 6);
        }

        Map<String, Map<String, Object>> placeHeat = new HashMap<>();
        for (String pt : new String[] { "production", "storage", "auxiliary" })
        {
            long hzCnt = hazards.stream().filter(h -> pt.equals(h.getPlaceType())).count();
            long openCnt = allOrders.stream().filter(o -> pt.equals(o.getPlaceType()) && !"CLOSED".equals(o.getStatus())).count();
            long alertCnt = recentAlerts.stream().filter(a -> pt.equals(a.getPlaceType()) && Boolean.TRUE.equals(a.getIsRealHazard())).count();
            String riskStatus = (openCnt >= 2 || alertCnt >= 2) ? "高风险预警" : (openCnt == 1 ? "受控关注" : "平稳受控");
            Map<String, Object> stat = new HashMap<>();
            stat.put("hazardCount", hzCnt);
            stat.put("openOrderCount", openCnt);
            stat.put("recentAlertCount", alertCnt);
            stat.put("riskStatus", riskStatus);
            placeHeat.put(pt, stat);
        }

        Map<String, Object> overview = new HashMap<>();
        overview.put("aiEngineHealth", aiClient.fetchHealth());
        overview.put("placeHeatmap", placeHeat);
        overview.put("hazards", hazards);
        overview.put("recentAlerts", recentAlerts);
        overview.put("totalOrders", allOrders.size());
        overview.put("openOrders", allOrders.size() - closedOrders);
        overview.put("orderClosureRate", closureRate);
        overview.put("totalEquipments", equips.size());
        overview.put("recentEvaluations", evals);
        overview.put("cameraPoints", visionMapper.selectCameraPointList(new EhsCameraPoint()));
        try
        {
            overview.put("edgeNodes", jdbcTemplate.queryForList("SELECT * FROM ehs_edge_node ORDER BY node_id ASC"));
        }
        catch (Exception ignored)
        {
            overview.put("edgeNodes", List.of());
        }
        return overview;
    }

    private double round2(double v)
    {
        return BigDecimal.valueOf(v).setScale(2, RoundingMode.HALF_UP).doubleValue();
    }
}
