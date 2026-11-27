package com.glihub.ehs.service;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.MessageDigest;
import java.text.SimpleDateFormat;
import java.util.ArrayList;
import java.util.Base64;
import java.util.Date;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONArray;
import com.alibaba.fastjson2.JSONObject;
import com.glihub.common.config.GliHubConfig;
import com.glihub.ehs.client.AiServiceClient;
import com.glihub.ehs.domain.EhsHazardOrder;
import com.glihub.ehs.domain.EhsVisionAlert;
import com.glihub.ehs.mapper.EhsVisionMapper;
import com.glihub.ehs.websocket.EhsWebSocketConfig;

@Service
public class EhsEdgeService
{
    @Autowired
    private JdbcTemplate jdbc;
    @Autowired
    private EhsVisionMapper visionMapper;
    @Autowired
    private EhsClosedLoopService closedLoopService;
    @Autowired
    private AiServiceClient aiClient;

    public boolean verifyEdgeToken(String providedToken)
    {
        String expected = GliHubConfig.getEdgeSharedToken();
        return expected == null || expected.isEmpty() || expected.equals(providedToken);
    }

    @Transactional
    public Map<String, Object> registerEdgeNode(Map<String, Object> req, String clientIp)
    {
        String nodeCode = String.valueOf(req.getOrDefault("nodeCode", "edge-01"));
        String nodeName = String.valueOf(req.getOrDefault("nodeName", nodeCode));
        String osArch = String.valueOf(req.getOrDefault("osArch", ""));
        String chipModel = String.valueOf(req.getOrDefault("chipModel", ""));
        String precision = String.valueOf(req.getOrDefault("precisionMode", "int8"));
        String modelCode = String.valueOf(req.getOrDefault("activeModelCode", "yolo26n.int8.onnx"));
        String sha = String.valueOf(req.getOrDefault("activeModelSha256", ""));
        String debugUrl = String.valueOf(req.getOrDefault("localDebugUrl", "http://127.0.0.1:8091"));

        Long nodeId = jdbc.queryForObject(
                """
                INSERT INTO ehs_edge_node (
                    node_code, node_name, ip_address, local_debug_url, os_arch, chip_model,
                    precision_mode, active_model_code, active_model_sha256, online_status, last_heartbeat_time
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'ONLINE', CURRENT_TIMESTAMP)
                ON CONFLICT (node_code) DO UPDATE SET
                    node_name = EXCLUDED.node_name,
                    ip_address = EXCLUDED.ip_address,
                    local_debug_url = EXCLUDED.local_debug_url,
                    os_arch = EXCLUDED.os_arch,
                    chip_model = EXCLUDED.chip_model,
                    precision_mode = EXCLUDED.precision_mode,
                    active_model_code = EXCLUDED.active_model_code,
                    active_model_sha256 = EXCLUDED.active_model_sha256,
                    online_status = 'ONLINE',
                    last_heartbeat_time = CURRENT_TIMESTAMP
                RETURNING node_id
                """,
                Long.class,
                nodeCode, nodeName, clientIp, debugUrl, osArch, chipModel, precision, modelCode, sha
        );

        Object rawChannels = req.get("channels");
        if (rawChannels instanceof List<?> list)
        {
            for (Object item : list)
            {
                JSONObject ch = JSON.parseObject(JSON.toJSONString(item));
                String chCode = ch.getString("channelCode");
                if (chCode == null || chCode.isEmpty()) continue;
                String roiJson = ch.getJSONArray("roiPolygon") != null
                        ? ch.getJSONArray("roiPolygon").toJSONString()
                        : "[[0.05,0.05],[0.95,0.05],[0.95,0.95],[0.05,0.95]]";
                jdbc.update(
                        """
                        INSERT INTO ehs_edge_channel (node_code, channel_code, channel_name, dept_id, place_type, task_type, roi_polygon_json, conf_threshold)
                        VALUES (?, ?, ?, ?, ?, ?, CAST(? AS jsonb), ?)
                        ON CONFLICT (node_code, channel_code) DO NOTHING
                        """,
                        nodeCode,
                        chCode,
                        ch.getOrDefault("channelName", chCode),
                        ch.getLongValue("deptId", 103L),
                        String.valueOf(ch.getOrDefault("placeType", "production")).toLowerCase(),
                        ch.getOrDefault("taskType", "detect"),
                        roiJson,
                        ch.getDoubleValue("confThreshold") > 0 ? ch.getDoubleValue("confThreshold") : 0.35
                );
            }
        }

        Integer cfgVer = jdbc.queryForObject("SELECT config_version FROM ehs_edge_node WHERE node_code = ?", Integer.class, nodeCode);
        Map<String, Object> out = new HashMap<>();
        out.put("nodeId", nodeId);
        out.put("heartbeatIntervalSec", 15);
        out.put("configVersion", cfgVer != null ? cfgVer : 1);
        return out;
    }

    @Transactional
    public Map<String, Object> handleHeartbeat(Map<String, Object> req, String serverBaseUrl)
    {
        String nodeCode = String.valueOf(req.getOrDefault("nodeCode", "edge-01"));
        double fps = req.get("fps") != null ? Double.parseDouble(String.valueOf(req.get("fps"))) : 0.0;
        double cpu = req.get("cpuPercent") != null ? Double.parseDouble(String.valueOf(req.get("cpuPercent"))) : 0.0;
        double mem = req.get("memMb") != null ? Double.parseDouble(String.valueOf(req.get("memMb"))) : 0.0;
        int qSize = req.get("queuePendingCount") != null ? Integer.parseInt(String.valueOf(req.get("queuePendingCount"))) : 0;
        String activeModel = String.valueOf(req.getOrDefault("activeModelCode", ""));
        String activeSha = String.valueOf(req.getOrDefault("activeModelSha256", ""));

        jdbc.update(
                """
                UPDATE ehs_edge_node
                SET current_fps = ?, cpu_percent = ?, mem_mb = ?, offline_queue_size = ?,
                    active_model_code = CASE WHEN ? <> '' THEN ? ELSE active_model_code END,
                    active_model_sha256 = CASE WHEN ? <> '' THEN ? ELSE active_model_sha256 END,
                    online_status = 'ONLINE', last_heartbeat_time = CURRENT_TIMESTAMP
                WHERE node_code = ?
                """,
                fps, cpu, mem, qSize, activeModel, activeModel, activeSha, activeSha, nodeCode
        );

        // If pending OTA matches activeSha, mark APPLIED!
        if (!activeSha.isEmpty())
        {
            jdbc.update(
                    "UPDATE ehs_edge_ota_task SET ota_status = 'APPLIED', finish_time = CURRENT_TIMESTAMP WHERE node_code = ? AND sha256_hex = ? AND ota_status IN ('PENDING','DOWNLOADING')",
                    nodeCode, activeSha
            );
        }

        List<Map<String, Object>> rows = jdbc.queryForList("SELECT config_version FROM ehs_edge_node WHERE node_code = ?", nodeCode);
        int desiredVer = rows.isEmpty() ? 1 : ((Number) rows.get(0).get("config_version")).intValue();

        Map<String, Object> resp = new HashMap<>();
        resp.put("ack", true);
        resp.put("desiredConfigVersion", desiredVer);

        List<Map<String, Object>> pendingOtas = jdbc.queryForList(
                "SELECT ota_id, target_model_file, sha256_hex FROM ehs_edge_ota_task WHERE node_code = ? AND ota_status = 'PENDING' ORDER BY ota_id DESC LIMIT 1",
                nodeCode
        );
        if (!pendingOtas.isEmpty())
        {
            Map<String, Object> ota = pendingOtas.get(0);
            String file = String.valueOf(ota.get("target_model_file"));
            Map<String, Object> cmd = new HashMap<>();
            cmd.put("otaId", ota.get("ota_id"));
            cmd.put("targetModelFile", file);
            cmd.put("sha256Hex", ota.get("sha256_hex"));
            cmd.put("downloadUrl", serverBaseUrl + "/ehs/edge/ota/download/" + file);
            resp.put("otaCommand", cmd);
            jdbc.update("UPDATE ehs_edge_ota_task SET ota_status = 'DOWNLOADING' WHERE ota_id = ?", ota.get("ota_id"));
        }
        return resp;
    }

    public Map<String, Object> fetchNodeRemoteConfig(String nodeCode)
    {
        List<Map<String, Object>> nodes = jdbc.queryForList("SELECT config_version FROM ehs_edge_node WHERE node_code = ?", nodeCode);
        int ver = nodes.isEmpty() ? 1 : ((Number) nodes.get(0).get("config_version")).intValue();
        List<Map<String, Object>> chRows = jdbc.queryForList(
                "SELECT channel_code, channel_name, dept_id, place_type, task_type, roi_polygon_json::text AS roi_json, conf_threshold, silence_window_sec FROM ehs_edge_channel WHERE node_code = ? ORDER BY channel_id ASC",
                nodeCode
        );
        List<Map<String, Object>> channels = new ArrayList<>();
        for (Map<String, Object> r : chRows)
        {
            Map<String, Object> c = new HashMap<>();
            c.put("channelCode", r.get("channel_code"));
            c.put("channelName", r.get("channel_name"));
            c.put("deptId", r.get("dept_id"));
            c.put("placeType", r.get("place_type"));
            c.put("taskType", r.get("task_type"));
            c.put("roiPolygon", JSON.parseArray(String.valueOf(r.get("roi_json"))));
            c.put("confThreshold", r.get("conf_threshold"));
            c.put("silenceWindowSec", r.get("silence_window_sec"));
            channels.add(c);
        }
        Map<String, Object> out = new HashMap<>();
        out.put("configVersion", ver);
        out.put("channels", channels);
        return out;
    }

    @Transactional
    public Map<String, Object> ingestEdgeAlertsBatch(Map<String, Object> payload)
    {
        String nodeCode = String.valueOf(payload.getOrDefault("nodeCode", "edge-node"));
        JSONArray events = JSON.parseArray(JSON.toJSONString(payload.getOrDefault("events", List.of())));

        List<String> acceptedUuids = new ArrayList<>();
        List<Long> createdOrderIds = new ArrayList<>();

        Path snapsDir = Paths.get(GliHubConfig.getEdgeSnapsDir()).toAbsolutePath();
        try { Files.createDirectories(snapsDir); } catch (Exception ignored) {}

        for (int i = 0; i < events.size(); i++)
        {
            JSONObject ev = events.getJSONObject(i);
            String alertUuid = ev.getString("alertUuid");
            if (alertUuid == null || alertUuid.isEmpty())
            {
                alertUuid = "edge-" + System.currentTimeMillis() + "-" + i;
            }

            // Serialize concurrent uploads of the same alertUuid across virtual threads
            jdbc.queryForObject("SELECT pg_advisory_xact_lock(hashtext(?))", Object.class, alertUuid);

            // Idempotent deduplication check for offline store-and-forward replay
            List<Long> existing = jdbc.queryForList(
                    "SELECT alert_id FROM ehs_vision_alert WHERE alert_uuid = ?", Long.class, alertUuid
            );
            if (!existing.isEmpty())
            {
                acceptedUuids.add(alertUuid);
                continue;
            }

            String thumbB64 = ev.getString("annotatedThumbB64");
            String cropB64 = ev.getString("cropImageB64");
            String chosenB64 = (thumbB64 != null && !thumbB64.isEmpty()) ? thumbB64 : cropB64;

            String publicUrl = "/sample-images/zidane.jpg";
            if (chosenB64 != null && !chosenB64.isEmpty())
            {
                try
                {
                    String clean = chosenB64.contains(",") ? chosenB64.substring(chosenB64.indexOf(",") + 1) : chosenB64;
                    byte[] imgBytes = Base64.getDecoder().decode(clean);
                    String fileName = alertUuid.replaceAll("[^a-zA-Z0-9_-]", "") + ".jpg";
                    Files.write(snapsDir.resolve(fileName), imgBytes);
                    publicUrl = "/edge-snaps/" + fileName;
                }
                catch (Exception ignored) {}
            }

            JSONArray dets = ev.getJSONArray("detections");
            if (dets == null) dets = new JSONArray();
            String placeType = String.valueOf(ev.getOrDefault("placeType", "production")).toLowerCase();
            long deptId = ev.getLongValue("deptId", 103L);
            String modelName = String.valueOf(ev.getOrDefault("modelName", "yolo26n.int8.onnx"));

            // Query RAG laws for edge violation
            JSONObject ragResp = aiClient.postJsonWithFallback(
                    "/api/v1/rag/search",
                    Map.of("query", "未佩戴安全帽 个体防护 作业场所违章", "place_type", placeType, "top_k", 2),
                    new JSONObject()
            );
            JSONArray citedLaws = ragResp != null && ragResp.getJSONArray("items") != null
                    ? ragResp.getJSONArray("items") : new JSONArray();

            String alertNo = "ED-" + new SimpleDateFormat("yyyyMMddHHmmss").format(new Date())
                    + "-" + ThreadLocalRandom.current().nextInt(100, 999);

            EhsVisionAlert alert = new EhsVisionAlert();
            alert.setAlertNo(alertNo);
            alert.setDeptId(deptId);
            alert.setPlaceType(placeType);
            alert.setModelCode(modelName);
            alert.setRawImageUrl(publicUrl);
            alert.setAnnotatedImageUrl(publicUrl);
            alert.setDetectionsJson(dets.toJSONString());
            alert.setInferenceMs(26);
            alert.setVlmReviewed(true);
            alert.setVlmModel("edge-cloud-v3-verifier");
            alert.setIsRealHazard(true);
            alert.setViolationType("边缘端实时违章抓拍 (" + ev.getOrDefault("taskType", "detect") + ")");
            alert.setSeverity("HIGH");
            alert.setVlmDescription("由独立边缘计算节点 [" + nodeCode + "] INT8 实时检出 " + dets.size() + " 处违章目标并经断网续传通道同步入库。");
            alert.setVlmSuggestion("请属地安全员立即前往现场核查督促整改，并上传复查照片完成 AI 销项闭环。");
            alert.setCitedLawsJson(citedLaws.toJSONString());
            alert.setHandleStatus("PENDING");
            alert.setCreateBy(nodeCode);
            visionMapper.insertAlert(alert);

            jdbc.update(
                    "UPDATE ehs_vision_alert SET alert_uuid = ?, source_node_code = ? WHERE alert_id = ?",
                    alertUuid, nodeCode, alert.getAlertId()
            );

            EhsHazardOrder order = closedLoopService.createOrderFromAlert(alert.getAlertId(), nodeCode);
            if (order != null && order.getOrderId() != null)
            {
                createdOrderIds.add(order.getOrderId());
            }

            EhsVisionAlert saved = visionMapper.selectAlertById(alert.getAlertId());
            EhsWebSocketConfig.broadcastEvent("EDGE_VISION_ALERT", saved);
            acceptedUuids.add(alertUuid);
        }

        Map<String, Object> out = new HashMap<>();
        out.put("acceptedUuids", acceptedUuids);
        out.put("acceptedCount", acceptedUuids.size());
        out.put("createdOrderIds", createdOrderIds);
        return out;
    }

    public List<Map<String, Object>> listEdgeNodesWithDetails()
    {
        jdbc.update("UPDATE ehs_edge_node SET online_status = 'OFFLINE' WHERE last_heartbeat_time < (CURRENT_TIMESTAMP - INTERVAL '60 seconds')");
        List<Map<String, Object>> nodes = jdbc.queryForList("SELECT * FROM ehs_edge_node ORDER BY node_id ASC");
        for (Map<String, Object> n : nodes)
        {
            String nc = String.valueOf(n.get("node_code"));
            List<Map<String, Object>> chs = jdbc.queryForList(
                    "SELECT channel_id, channel_code, channel_name, dept_id, place_type, task_type, roi_polygon_json::text AS roi_json, conf_threshold, silence_window_sec, dynamic_fps_enabled FROM ehs_edge_channel WHERE node_code = ? ORDER BY channel_id ASC",
                    nc
            );
            for (Map<String, Object> c : chs)
            {
                c.put("roiPolygon", JSON.parseArray(String.valueOf(c.get("roi_json"))));
            }
            n.put("channels", chs);
            n.put("otaHistory", jdbc.queryForList(
                    "SELECT ota_id, target_model_file, sha256_hex, precision_mode, ota_status, create_time, finish_time FROM ehs_edge_ota_task WHERE node_code = ? ORDER BY ota_id DESC LIMIT 5",
                    nc
            ));
        }
        return nodes;
    }

    @Transactional
    public Map<String, Object> updateChannelRoi(Map<String, Object> req)
    {
        String nodeCode = String.valueOf(req.getOrDefault("nodeCode", "edge-chem-zone-01"));
        String channelCode = String.valueOf(req.getOrDefault("channelCode", "cam-tank-01"));
        String taskType = String.valueOf(req.getOrDefault("taskType", "detect"));
        double conf = req.get("confThreshold") != null ? Double.parseDouble(String.valueOf(req.get("confThreshold"))) : 0.35;
        String roiJson = JSON.toJSONString(req.getOrDefault("roiPolygon", List.of()));

        jdbc.update(
                """
                UPDATE ehs_edge_channel
                SET roi_polygon_json = CAST(? AS jsonb), task_type = ?, conf_threshold = ?, update_time = CURRENT_TIMESTAMP
                WHERE node_code = ? AND channel_code = ?
                """,
                roiJson, taskType, conf, nodeCode, channelCode
        );
        jdbc.update("UPDATE ehs_edge_node SET config_version = config_version + 1 WHERE node_code = ?", nodeCode);
        return fetchNodeRemoteConfig(nodeCode);
    }

    public List<Map<String, Object>> listAvailableOtaModels()
    {
        List<Map<String, Object>> out = new ArrayList<>();
        File dir = new File(GliHubConfig.getModelsDir());
        File[] files = dir.listFiles((d, name) -> name.endsWith(".onnx"));
        if (files == null) return out;
        for (File f : files)
        {
            Map<String, Object> m = new HashMap<>();
            m.put("fileName", f.getName());
            m.put("sizeMb", Math.round((f.length() / (1024.0 * 1024.0)) * 100.0) / 100.0);
            m.put("precision", f.getName().contains(".int8.") ? "int8" : (f.getName().contains(".fp16.") ? "fp16" : "fp32"));
            m.put("sha256", computeFileSha256(f.toPath()));
            out.add(m);
        }
        return out;
    }

    @Transactional
    public Map<String, Object> createOtaTask(String nodeCode, String modelFile, String operator)
    {
        Path p = Paths.get(GliHubConfig.getModelsDir(), new File(modelFile).getName());
        if (!Files.exists(p))
        {
            throw new IllegalArgumentException("模型文件不存在: " + modelFile);
        }
        String sha = computeFileSha256(p);
        String prec = modelFile.contains(".int8.") ? "int8" : (modelFile.contains(".fp16.") ? "fp16" : "fp32");
        Long otaId = jdbc.queryForObject(
                """
                INSERT INTO ehs_edge_ota_task (node_code, target_model_file, sha256_hex, precision_mode, ota_status, create_by)
                VALUES (?, ?, ?, ?, 'PENDING', ?)
                RETURNING ota_id
                """,
                Long.class, nodeCode, p.getFileName().toString(), sha, prec, operator
        );
        Map<String, Object> res = new HashMap<>();
        res.put("otaId", otaId);
        res.put("nodeCode", nodeCode);
        res.put("targetModelFile", p.getFileName().toString());
        res.put("sha256Hex", sha);
        res.put("status", "PENDING");
        return res;
    }

    private String computeFileSha256(Path path)
    {
        try
        {
            MessageDigest md = MessageDigest.getInstance("SHA-256");
            byte[] buf = Files.readAllBytes(path);
            byte[] dig = md.digest(buf);
            StringBuilder sb = new StringBuilder();
            for (byte b : dig) sb.append(String.format("%02x", b));
            return sb.toString();
        }
        catch (Exception ex)
        {
            return "";
        }
    }
}
