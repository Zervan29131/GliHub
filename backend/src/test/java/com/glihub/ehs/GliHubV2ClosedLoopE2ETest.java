package com.glihub.ehs;

import static org.junit.jupiter.api.Assertions.*;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.*;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.*;

import java.util.List;
import java.util.Map;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.boot.webmvc.test.autoconfigure.AutoConfigureMockMvc;
import org.springframework.http.MediaType;
import org.springframework.security.test.context.support.WithMockUser;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.MvcResult;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;

@SpringBootTest(webEnvironment = SpringBootTest.WebEnvironment.RANDOM_PORT)
@AutoConfigureMockMvc
public class GliHubV2ClosedLoopE2ETest
{
    @Autowired
    private MockMvc mockMvc;

    @Test
    @WithMockUser(username = "admin", roles = { "admin" })
    public void testFullClosedLoopAndEdgeCloudPipeline() throws Exception
    {
        // 1. 中心 ONNX INT8 视觉检测 -> VLM 二次复核 -> RAG 法条匹配 -> 自动生成隐患工单
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

        JSONObject data = JSON.parseObject(detectMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertNotNull(data);
        assertTrue(data.getJSONObject("vision").getJSONArray("detections").size() > 0);
        assertTrue(data.getJSONObject("vlmReview").getBooleanValue("is_real_hazard"));
        assertFalse(data.getJSONArray("citedLaws").isEmpty());

        JSONObject autoOrder = data.getJSONObject("autoCreatedOrder");
        assertNotNull(autoOrder);
        Long orderId = autoOrder.getLong("orderId");
        assertEquals("OPEN", autoOrder.getString("status"));

        // 2. 作业区动态风险联动与确定性安全评价参数辅助
        MvcResult dynMvc = mockMvc.perform(get("/ehs/evaluate/dynamic-status")
                        .param("deptId", "103")
                        .param("placeType", "production"))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject dynData = JSON.parseObject(dynMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertTrue(dynData.getBooleanValue("reEvalTriggered"));

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
        assertTrue(assistData.getBooleanValue("requires_human_confirm"));

        // 3. 四大确定性安全评价结果 (Dow F&EI / LEC / TNT / SCL) 生成注册安全工程师报告
        String reportReq = JSON.toJSONString(Map.of(
                "placeType", "production",
                "deptId", 103,
                "areaName", "采油作业区",
                "evaluator", "JDK25-E2E验收",
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
        assertNotNull(repData.getLong("savedEvalId"));
        assertTrue(repData.getString("report_markdown").contains("881.86"));

        // 4. 重大危险源 TNT 事故后果推演与《现场应急处置行动卡》
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
        assertTrue(simData.getString("actionCardMarkdown").contains("应急处置行动卡"));

        // 5. 合规复查照片 AI 核验自动销项闭环
        String rectifyReq = JSON.toJSONString(Map.of(
                "sampleRelPath", "archive/images/BikesHelmets0.png",
                "rectifyNote", "违章人员已规范补戴安全帽并通过复检"
        ));
        MvcResult recMvc = mockMvc.perform(post("/ehs/order/" + orderId + "/rectify-sample")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(rectifyReq))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject recData = JSON.parseObject(recMvc.getResponse().getContentAsString()).getJSONObject("data");
        assertEquals("CLOSED", recData.getJSONObject("order").getString("status"));

        // 6. GliHub 3.0 边缘计算节点注册、心跳、断网续传幂等接收与 ROI 更新验证
        String edgeToken = "glihub-edge-shared-token-v3";
        mockMvc.perform(post("/ehs/edge/register")
                        .header("X-Edge-Token", edgeToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(JSON.toJSONString(Map.of(
                                "nodeCode", "edge-chem-zone-01",
                                "nodeName", "一车间危化品罐区边缘盒子 #01",
                                "osArch", "darwin-arm64",
                                "chipModel", "Apple M1 Pro",
                                "precisionMode", "int8",
                                "activeModelCode", "yolo26n.int8.onnx"
                        ))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.code").value(200));

        String uniqueAlertUuid = "edge-e2e-" + UUID.randomUUID().toString().substring(0, 12);
        String edgeBatchPayload = JSON.toJSONString(Map.of(
                "nodeCode", "edge-chem-zone-01",
                "events", List.of(Map.of(
                        "alertUuid", uniqueAlertUuid,
                        "channelCode", "cam-tank-01",
                        "deptId", 103,
                        "placeType", "production",
                        "taskType", "detect",
                        "modelName", "yolo26n.int8.onnx",
                        "detections", List.of(Map.of("class_name", "no_helmet", "confidence", 0.91, "bbox", List.of(100, 120, 240, 420)))
                ))
        ));

        MvcResult batch1 = mockMvc.perform(post("/ehs/edge/alerts/batch")
                        .header("X-Edge-Token", edgeToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(edgeBatchPayload))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject b1Data = JSON.parseObject(batch1.getResponse().getContentAsString()).getJSONObject("data");
        assertEquals(1, b1Data.getJSONArray("createdOrderIds").size(), "首次上报应创建 1 张工单");

        // 重放同一批 alertUuid 验证断网续传严格幂等去重
        MvcResult batch2 = mockMvc.perform(post("/ehs/edge/alerts/batch")
                        .header("X-Edge-Token", edgeToken)
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(edgeBatchPayload))
                .andExpect(status().isOk())
                .andReturn();
        JSONObject b2Data = JSON.parseObject(batch2.getResponse().getContentAsString()).getJSONObject("data");
        assertEquals(0, b2Data.getJSONArray("createdOrderIds").size(), "断网重传相同 alertUuid 必须幂等去重不重复建单");

        // 7. GliHub 3.0 七大插件中心与 OpenAPI 3.1 契约校验
        MvcResult pluginsMvc = mockMvc.perform(get("/ehs/plugins"))
                .andExpect(status().isOk())
                .andReturn();
        JSONArray plugins = JSON.parseObject(pluginsMvc.getResponse().getContentAsString())
                .getJSONObject("data").getJSONArray("plugins");
        assertEquals(7, plugins.size(), "模型选装中心应返回完整 7 层插件状态");

        mockMvc.perform(get("/v3/api-docs"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.info.version").value("3.0.0"));

        System.out.println("=== GLIHUB_3_0_SPRING_BOOT_4_2_JDK_25_E2E_PASSED ===");
    }
}
