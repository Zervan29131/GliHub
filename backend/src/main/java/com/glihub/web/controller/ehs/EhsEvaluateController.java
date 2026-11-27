package com.glihub.web.controller.ehs;

import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.glihub.common.core.controller.BaseController;
import com.glihub.common.core.domain.AjaxResult;
import com.glihub.common.core.page.TableDataInfo;
import com.glihub.ehs.client.AiServiceClient;
import com.glihub.ehs.domain.EhsEvalRecord;
import com.glihub.ehs.domain.EhsHazardProfile;
import com.glihub.ehs.mapper.EhsEvalRecordMapper;
import com.glihub.ehs.mapper.EhsHazardOrderMapper;
import com.glihub.ehs.mapper.EhsHazardProfileMapper;
import com.glihub.ehs.mapper.EhsVisionMapper;
import com.glihub.ehs.service.EhsClosedLoopService;

@RestController
@RequestMapping("/ehs/evaluate")
public class EhsEvaluateController extends BaseController
{
    @Autowired
    private EhsClosedLoopService closedLoopService;
    @Autowired
    private EhsEvalRecordMapper evalMapper;
    @Autowired
    private EhsHazardProfileMapper profileMapper;
    @Autowired
    private EhsVisionMapper visionMapper;
    @Autowired
    private EhsHazardOrderMapper orderMapper;
    @Autowired
    private AiServiceClient aiClient;

    @GetMapping("/dynamic-status")
    public AjaxResult dynamicStatus(
            @RequestParam(value = "deptId", required = false) Long deptId,
            @RequestParam(value = "placeType", defaultValue = "production") String placeType)
    {
        return success(closedLoopService.getDynamicRiskStatus(deptId, placeType));
    }

    @GetMapping("/records")
    public TableDataInfo listRecords(EhsEvalRecord query)
    {
        startPage();
        List<EhsEvalRecord> rows = evalMapper.selectRecordList(query);
        return getDataTable(rows);
    }

    @PostMapping("/calc-and-save")
    public AjaxResult archiveCalc(@RequestBody EhsEvalRecord record)
    {
        if (record.getEvalNo() == null || record.getEvalNo().isEmpty())
        {
            record.setEvalNo("EV-" + System.currentTimeMillis() + "-" + ThreadLocalRandom.current().nextInt(10, 99));
        }
        int alertCnt = visionMapper.countRecentRealAlertsByDept(record.getDeptId());
        int orderCnt = orderMapper.countOpenOrdersByDept(record.getDeptId());
        record.setDynamicAlertCount(alertCnt);
        record.setOpenOrderCount(orderCnt);
        record.setReEvalRecommended((alertCnt + orderCnt) >= 2);
        record.setCreateBy(currentUser());
        evalMapper.insertRecord(record);
        return success(record);
    }

    @PostMapping("/ai-assist")
    public AjaxResult aiParamAssist(@RequestBody Map<String, Object> body)
    {
        Long deptId = body.get("deptId") != null ? Long.valueOf(String.valueOf(body.get("deptId"))) : null;
        String method = String.valueOf(body.getOrDefault("evalMethod", "LEC"));
        String placeType = String.valueOf(body.getOrDefault("placeType", "production"));
        String areaName = String.valueOf(body.getOrDefault("areaName", "采油作业区"));

        int alerts = visionMapper.countRecentRealAlertsByDept(deptId);
        int orders = orderMapper.countOpenOrdersByDept(deptId);

        EhsHazardProfile q = new EhsHazardProfile();
        q.setDeptId(deptId);
        List<EhsHazardProfile> hzList = profileMapper.selectProfileList(q);

        Map<String, Object> aiReq = new HashMap<>();
        aiReq.put("eval_method", method);
        aiReq.put("place_type", placeType);
        aiReq.put("area_name", areaName);
        aiReq.put("recent_alerts_count", alerts);
        aiReq.put("open_orders_count", orders);
        if (!hzList.isEmpty())
        {
            EhsHazardProfile h = hzList.get(0);
            aiReq.put("hazard_profile", Map.of(
                    "chemical_name", h.getChemicalName() != null ? h.getChemicalName() : "",
                    "dow_mf", h.getDowMf() != null ? h.getDowMf() : 16,
                    "major_hazard_grade", h.getMajorHazardGrade() != null ? h.getMajorHazardGrade() : "",
                    "risk_level", h.getRiskLevel() != null ? h.getRiskLevel() : ""
            ));
        }

        JSONObject fallback = new JSONObject();
        fallback.put("eval_method", method);
        fallback.put("requires_human_confirm", true);
        fallback.put("dynamic_re_eval_triggered", (alerts + orders) >= 2);
        if ("DOW".equalsIgnoreCase(method))
        {
            fallback.put("recommended_params", Map.of("mf", 16, "f1", 2.0, "f2", 1.9, "cFactor", 0.72));
        }
        else
        {
            fallback.put("recommended_params", Map.of("l", (alerts + orders) >= 2 ? 6.0 : 3.0, "e", 6.0, "c", 7.0));
        }
        fallback.put("rationale_items", List.of("基于本地确定性动态规则库生成建议参数，请安全评价工程师复核确认。"));

        return success(aiClient.postJsonWithFallback("/api/v1/agents/eval-assist", aiReq, fallback));
    }

    @PostMapping("/ai-report")
    public AjaxResult generateAndSaveReport(@RequestBody Map<String, Object> body)
    {
        String placeType = String.valueOf(body.getOrDefault("placeType", "production"));
        String areaName = String.valueOf(body.getOrDefault("areaName", "采油作业区"));
        Long deptId = body.get("deptId") != null ? Long.valueOf(String.valueOf(body.get("deptId"))) : null;
        Object evalSummary = body.getOrDefault("evalSummary", new HashMap<>());

        int alerts = visionMapper.countRecentRealAlertsByDept(deptId);
        int orders = orderMapper.countOpenOrdersByDept(deptId);
        EhsHazardProfile hq = new EhsHazardProfile();
        hq.setPlaceType(placeType);
        List<EhsHazardProfile> hzList = profileMapper.selectProfileList(hq);

        Map<String, Object> aiReq = new HashMap<>();
        aiReq.put("place_type", placeType);
        aiReq.put("area_name", areaName);
        aiReq.put("eval_summary", evalSummary);
        aiReq.put("hazard_profiles", hzList);
        aiReq.put("alert_stats", Map.of("total", alerts));
        aiReq.put("order_stats", Map.of("open", orders));

        JSONObject fb = new JSONObject();
        fb.put("report_markdown", "# " + areaName + " 安全评价报告（离线模板）\n\n- 近期告警数：" + alerts + "\n- 待闭环隐患工单：" + orders + "\n- 四大确定性算法计算指标已归档入库。");
        fb.put("generated_by", "backend-offline-template");
        JSONObject aiOut = aiClient.postJsonWithFallback("/api/v1/agents/eval-report", aiReq, fb);

        EhsEvalRecord rec = new EhsEvalRecord();
        rec.setEvalNo("RP-" + System.currentTimeMillis());
        rec.setPlaceType(placeType);
        rec.setDeptId(deptId);
        rec.setAreaName(areaName);
        rec.setEvalMethod("COMPREHENSIVE");
        rec.setInputParamsJson(JSON.toJSONString(body));
        rec.setResultMetricsJson(JSON.toJSONString(evalSummary));
        rec.setRiskGrade(orders > 0 ? "需限期整改" : "风险受控");
        rec.setDynamicAlertCount(alerts);
        rec.setOpenOrderCount(orders);
        rec.setReEvalRecommended((alerts + orders) >= 2);
        rec.setAiReportMarkdown(aiOut.getString("report_markdown"));
        rec.setEvaluator(String.valueOf(body.getOrDefault("evaluator", currentUser())));
        rec.setCreateBy(currentUser());
        evalMapper.insertRecord(rec);

        aiOut.put("savedEvalId", rec.getEvalId());
        aiOut.put("evalNo", rec.getEvalNo());
        return success(aiOut);
    }

    @PostMapping("/tnt-impact")
    public AjaxResult tntImpact(@RequestBody Map<String, Object> body)
    {
        Long hazardId = body.get("hazardId") != null ? Long.valueOf(String.valueOf(body.get("hazardId"))) : null;
        double r1 = Double.parseDouble(String.valueOf(body.getOrDefault("r1", 15)));
        double r2 = Double.parseDouble(String.valueOf(body.getOrDefault("r2", 35)));
        double r3 = Double.parseDouble(String.valueOf(body.getOrDefault("r3", 65)));
        double r4 = Double.parseDouble(String.valueOf(body.getOrDefault("r4", 40)));
        return success(closedLoopService.computeTntSpatialImpact(hazardId, r1, r2, r3, r4));
    }

    private String currentUser()
    {
        try { return getUsername(); } catch (Exception e) { return "admin"; }
    }
}
