package com.glihub.web.controller.ehs;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.web.bind.annotation.*;
import com.alibaba.fastjson2.JSONObject;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.core.controller.BaseController;
import com.glihub.common.core.domain.AjaxResult;
import com.glihub.ehs.client.AiServiceClient;

@RestController
@RequestMapping("/ehs/plugins")
public class EhsAiPluginController extends BaseController
{
    @Autowired
    private AiServiceClient aiClient;
    @Autowired
    private JdbcTemplate jdbc;

    @GetMapping
    public AjaxResult listPlugins()
    {
        JSONObject fallback = new JSONObject();
        fallback.put("deploy_profile", "cpu-int8");
        fallback.put("plugins", List.of());
        fallback.put("degraded", true);
        JSONObject live = aiClient.getJsonWithFallback("/api/v1/plugins", fallback);
        return success(live);
    }

    @PostMapping("/{pluginId}/toggle")
    public AjaxResult togglePlugin(@PathVariable String pluginId, @RequestBody Map<String, Object> req)
    {
        Boolean enabled = req.get("enabled") != null ? Boolean.valueOf(String.valueOf(req.get("enabled"))) : null;
        String prec = req.get("preferred_precision") != null ? String.valueOf(req.get("preferred_precision")) : null;
        String endpoint = req.get("provider_endpoint") != null ? String.valueOf(req.get("provider_endpoint")) : null;
        String model = req.get("provider_model") != null ? String.valueOf(req.get("provider_model")) : null;

        jdbc.update(
                """
                INSERT INTO ehs_ai_plugin_config (plugin_id, enabled, preferred_precision, provider_endpoint, provider_model, update_time)
                VALUES (?, COALESCE(?, TRUE), COALESCE(?, 'int8'), COALESCE(?, ''), COALESCE(?, ''), CURRENT_TIMESTAMP)
                ON CONFLICT (plugin_id) DO UPDATE SET
                    enabled = COALESCE(?, ehs_ai_plugin_config.enabled),
                    preferred_precision = COALESCE(?, ehs_ai_plugin_config.preferred_precision),
                    provider_endpoint = COALESCE(?, ehs_ai_plugin_config.provider_endpoint),
                    provider_model = COALESCE(?, ehs_ai_plugin_config.provider_model),
                    update_time = CURRENT_TIMESTAMP
                """,
                pluginId, enabled, prec, endpoint, model, enabled, prec, endpoint, model
        );

        JSONObject fb = new JSONObject();
        fb.put("status", "saved_offline");
        return success(aiClient.postJsonWithFallback("/api/v1/plugins/" + pluginId + "/toggle", req, fb));
    }

    @PostMapping("/profile")
    public AjaxResult switchPrecisionProfile(@RequestBody Map<String, Object> req)
    {
        JSONObject fb = new JSONObject();
        fb.put("status", "offline");
        return success(aiClient.postJsonWithFallback("/api/v1/precision/profile", req, fb));
    }

    @PostMapping("/open-vocab")
    public AjaxResult testOpenVocab(@RequestBody Map<String, Object> req)
    {
        Map<String, Object> payload = new HashMap<>(req);
        if (req.get("sampleRelPath") != null && req.get("image_path") == null)
        {
            String rel = String.valueOf(req.get("sampleRelPath"));
            if (!rel.contains(".."))
            {
                File f = new File(GliHubConfig.getSampleImageDir(), rel).getAbsoluteFile();
                payload.put("image_path", f.getAbsolutePath());
            }
        }
        JSONObject fb = new JSONObject();
        fb.put("degraded", true);
        return success(aiClient.postJsonWithFallback("/api/v1/vision/open-vocab", payload, fb));
    }
}
