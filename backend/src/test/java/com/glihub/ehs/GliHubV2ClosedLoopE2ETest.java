package com.glihub.ehs;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.util.Map;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;

/**
 * GliHub 2.0 端到端全链路自动化验收测试：
 * 验证「yolov5target-main 检测 -> VLM 二次复核 -> 法规溯源 -> 自动生成隐患工单 -> 动态风险重评 -> AI 评价报告 -> 事故推演 -> 整改复检销项」全闭环
 */
@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
public class GliHubV2ClosedLoopE2ETest
{
    @Autowired
    private MockMvc mockMvc;

    @Test
    @WithMockUser(username = "admin", roles = { "admin" })
    public void testFullClosedLoopPipeline() throws Exception
    {
        // 1. 调用存量 yolov5target-main 模型检测未佩戴安全帽样本图 -> VLM 复核 -> RAG 法条匹配 -> 自动生成隐患工单
        String detectReq = JSON.toJSONString(Map.of(
                "sampleRelPath", "zidane.jpg",
                "deptId", 103,
                "placeType", "production",
                "modelCode", "yolov5_helmet_local",
                "confThres", 0.35,
                "enableVlm", true
        ));
        MvcResult detectMvc = mockMvc.perform(post("/ehs/vision/detect/sample")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(detectReq))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andReturn();

        JSONObject detectBody = JSON.parseObject(detectMvc.getResponse().getContentAsString());
        JSONObject data = detectBody.getJSONObject("data");
        assertNotNull(data, "检测响应 data 不能为空");

        JSONObject vision = data.getJSONObject("vision");
        JSONArray detections = vision.getJSONArray("detections");
        assertTrue(detections.size() > 0, "yolov5target-main 应检出违章目标框");

        JSONObject vlmReview = data.getJSONObject("vlmReview");
        assertNotNull(vlmReview, "VLM 二次复核结果不能为空");
        assertTrue(vlmReview.getBooleanValue("is_real_hazard"), "应复核判定为真实隐患");

        JSONArray citedLaws = data.getJSONArray("citedLaws");
        assertTrue(citedLaws != null && !citedLaws.isEmpty(), "RAG 应自动匹配引用《安全生产法》条款");

        JSONObject autoOrder = data.getJSONObject("autoCreatedOrder");
        assertNotNull(autoOrder, "HIGH 级真实视觉隐患应自动派发隐患整改工单");
        Long orderId = autoOrder.getLong("orderId");
        assertNotNull(orderId);
        assertEquals("OPEN", autoOrder.getString("status"));
        assertTrue(autoOrder.getString("legalBasis").contains("安全生产法"), "工单应自动关联触犯法规依据");

        // 2. 验证作业区动态风险联动预警与 AI 评价参数推荐
        MvcResult dynMvc = mockMvc.perform(get("/ehs/evaluate/dynamic-status")
                        .param("deptId", "103")
                        .param("placeType", "production"))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject dynData = JSON.parseObject(dynMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertTrue(dynData.getBooleanValue("reEvalTriggered"), "存在未闭环隐患工单与高危告警时应触发 LEC 动态重评预警");

        String assistReq = JSON.toJSONString(Map.of(
                "evalMethod", "LEC",
                "placeType", "production",
                "deptId", 103,
                "areaName", "采油作业区"
        ));
        MvcResult assistMvc = mockMvc.perform(post("/ehs/evaluate/ai-assist")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(assistReq))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject assistData = JSON.parseObject(assistMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertTrue(assistData.getBooleanValue("requires_human_confirm"), "AI 参数建议必须标记需人工审核确认");

        // 3. 验证 TNT 空间波及检索与一键生成专业安全评价报告
        String reportReq = JSON.toJSONString(Map.of(
                "placeType", "production",
                "deptId", 103,
                "areaName", "采油作业区",
                "evaluator", "E2E自动化验收",
                "evalSummary", Map.of(
                        "dow", Map.of("unitName", "合成气装置", "f3", "3.80", "fei", "60.80", "compensatedFei", "43.78", "radius", "15.56", "area", "761.08", "level", "较轻", "compLevel", "最轻"),
                        "lec", Map.of("jobName", "动火巡检", "d", "252.00", "grade", "2级风险", "levelText", "需立即整改"),
                        "tnt", Map.of("wtnt", "881.86", "r1", "13.00", "r2", "32.58", "r3", "60.37", "r4", "29.15"),
                        "scl", Map.of("total", 4, "pass", 4, "fail", 0, "rate", 100)
                )
        ));
        MvcResult repMvc = mockMvc.perform(post("/ehs/evaluate/ai-report")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(reportReq))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject repData = JSON.parseObject(repMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertNotNull(repData.getLong("savedEvalId"), "生成的 AI 安全评价报告应持久化归档");
        assertTrue(repData.getString("report_markdown").contains("道氏"), "报告正文应包含确定性评价结论");

        // 4. 验证重大危险源事故推演生成《现场应急处置行动卡》
        String simReq = JSON.toJSONString(Map.of(
                "hazardId", 2,
                "accidentType", "甲醇储罐蒸气云爆炸",
                "leakMassKg", 5000,
                "windDirection", "东南风",
                "windSpeedMs", 3.5
        ));
        MvcResult simMvc = mockMvc.perform(post("/ehs/emergency/simulate")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(simReq))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject simData = JSON.parseObject(simMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertTrue(simData.getString("actionCardMarkdown").contains("应急处置行动卡"), "应生成结构化现场应急处置行动卡");

        // 5. 提交合规复查图触发 AI 自动复检销项闭环
        String rectifyReq = JSON.toJSONString(Map.of(
                "sampleRelPath", "archive/images/BikesHelmets0.png",
                "rectifyNote", "现场违章人员已补戴标准安全帽并通过复查"
        ));
        MvcResult recMvc = mockMvc.perform(post("/ehs/order/" + orderId + "/rectify-sample")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(rectifyReq))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject recData = JSON.parseObject(recMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertEquals("CLOSED", recData.getJSONObject("order").getString("status"), "AI 复检通过后隐患工单应自动流转为 CLOSED");

        // 6. 验证全域态势指挥大屏总览接口
        mockMvc.perform(get("/ehs/dashboard/overview"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200))
                .andExpect(jsonPath("$.data.hazards").isArray());

        System.out.println("=== GLIHUB_2_0_FULL_E2E_CLOSED_LOOP_PASSED ===");
    }
}
