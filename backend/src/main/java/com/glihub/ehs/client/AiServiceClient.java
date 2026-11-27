package com.glihub.ehs.client;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;
import java.util.Collections;
import java.util.Map;
import java.util.function.Consumer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpEntity;
import org.springframework.http.HttpHeaders;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.web.client.RestTemplate;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.glihub.common.config.GliHubConfig;
import com.glihub.system.service.ISysConfigService;
import org.springframework.beans.factory.annotation.Autowired;

/**
 * FastAPI ai-service 编排网关客户端（内置连接探活与离线熔断降级机制）
 */
@Component
public class AiServiceClient
{
    private static final Logger log = LoggerFactory.getLogger(AiServiceClient.class);

    @Autowired
    private ISysConfigService sysConfigService;

    private RestTemplate buildTemplate(int readTimeoutMs)
    {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(2500);
        factory.setReadTimeout(readTimeoutMs);
        return new RestTemplate(factory);
    }

    public boolean isAiEnabled()
    {
        String flag = sysConfigService.selectConfigByKey("ehs.ai.enabled");
        return flag == null || !"false".equalsIgnoreCase(flag.trim());
    }

    public JSONObject fetchHealth()
    {
        if (!isAiEnabled())
        {
            JSONObject disabled = new JSONObject();
            disabled.put("status", "disabled");
            disabled.put("message", "已通过系统参数 ehs.ai.enabled=false 关闭协同服务");
            return disabled;
        }
        try
        {
            String url = GliHubConfig.getAiServiceUrl() + "/api/v1/health";
            String body = buildTemplate(3000).getForObject(url, String.class);
            return JSON.parseObject(body);
        }
        catch (Exception ex)
        {
            JSONObject down = new JSONObject();
            down.put("status", "degraded");
            down.put("message", "AI 微服务离线，已自动切换至本地确定性规则模式: " + ex.getMessage());
            return down;
        }
    }

    public JSONObject getJsonWithFallback(String apiPath, JSONObject fallback)
    {
        if (!isAiEnabled())
        {
            return fallback;
        }
        try
        {
            String url = GliHubConfig.getAiServiceUrl() + apiPath;
            String body = buildTemplate(5000).getForObject(url, String.class);
            if (body != null)
            {
                return JSON.parseObject(body);
            }
        }
        catch (Exception ex)
        {
            log.warn("GET ai-service [{}] 触发降级: {}", apiPath, ex.getMessage());
        }
        return fallback;
    }

    public JSONObject postJsonWithFallback(String apiPath, Map<String, Object> payload, JSONObject fallback)
    {
        if (!isAiEnabled())
        {
            return fallback;
        }
        try
        {
            String url = GliHubConfig.getAiServiceUrl() + apiPath;
            HttpHeaders headers = new HttpHeaders();
            headers.setContentType(MediaType.APPLICATION_JSON);
            HttpEntity<String> entity = new HttpEntity<>(JSON.toJSONString(payload), headers);
            ResponseEntity<String> resp = buildTemplate(GliHubConfig.getAiTimeoutMs())
                    .postForEntity(url, entity, String.class);
            if (resp.getStatusCode().is2xxSuccessful() && resp.getBody() != null)
            {
                return JSON.parseObject(resp.getBody());
            }
        }
        catch (Exception ex)
        {
            log.warn("调用 ai-service [{}] 触发熔断降级: {}", apiPath, ex.getMessage());
        }
        return fallback;
    }

    public void streamSsePost(String apiPath, Map<String, Object> payload, Consumer<String> onDataLine, Runnable onFallback)
    {
        if (!isAiEnabled())
        {
            onFallback.run();
            return;
        }
        HttpURLConnection conn = null;
        try
        {
            URL url = new URL(GliHubConfig.getAiServiceUrl() + apiPath);
            conn = (HttpURLConnection) url.openConnection();
            conn.setRequestMethod("POST");
            conn.setConnectTimeout(2500);
            conn.setReadTimeout(GliHubConfig.getAiTimeoutMs());
            conn.setDoOutput(true);
            conn.setRequestProperty("Content-Type", "application/json;charset=UTF-8");
            conn.setRequestProperty("Accept", "text/event-stream");
            byte[] bytes = JSON.toJSONString(payload).getBytes(StandardCharsets.UTF_8);
            try (OutputStream os = conn.getOutputStream())
            {
                os.write(bytes);
                os.flush();
            }
            if (conn.getResponseCode() != 200)
            {
                onFallback.run();
                return;
            }
            try (BufferedReader reader = new BufferedReader(
                    new InputStreamReader(conn.getInputStream(), StandardCharsets.UTF_8)))
            {
                String line;
                while ((line = reader.readLine()) != null)
                {
                    if (line.startsWith("data:"))
                    {
                        onDataLine.accept(line.substring(5).trim());
                    }
                }
            }
        }
        catch (Exception ex)
        {
            log.warn("SSE 流式请求 [{}] 离线降级: {}", apiPath, ex.getMessage());
            onFallback.run();
        }
        finally
        {
            if (conn != null)
            {
                conn.disconnect();
            }
        }
    }

    public JSONObject emptyListFallback(String key)
    {
        JSONObject obj = new JSONObject();
        obj.put(key, Collections.emptyList());
        obj.put("degraded", true);
        return obj;
    }
}
