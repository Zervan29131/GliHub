package com.glihub.ehs.websocket;

import java.util.Set;
import java.util.concurrent.CopyOnWriteArraySet;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.CloseStatus;
import org.springframework.web.socket.TextMessage;
import org.springframework.web.socket.WebSocketSession;
import org.springframework.web.socket.config.annotation.EnableWebSocket;
import org.springframework.web.socket.config.annotation.WebSocketConfigurer;
import org.springframework.web.socket.config.annotation.WebSocketHandlerRegistry;
import org.springframework.web.socket.handler.TextWebSocketHandler;
import com.alibaba.fastjson2.JSON;

/**
 * EHS 实时视觉告警与工单状态广播通道 (/ws/alerts)
 */
@Configuration
@EnableWebSocket
public class EhsWebSocketConfig implements WebSocketConfigurer
{
    private static final Logger log = LoggerFactory.getLogger(EhsWebSocketConfig.class);
    private static final Set<WebSocketSession> SESSIONS = new CopyOnWriteArraySet<>();

    @Bean
    public AlertSocketHandler alertSocketHandler()
    {
        return new AlertSocketHandler();
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry)
    {
        registry.addHandler(alertSocketHandler(), "/ws/alerts").setAllowedOriginPatterns("*");
    }

    public static void broadcastEvent(String eventType, Object data)
    {
        if (SESSIONS.isEmpty())
        {
            return;
        }
        java.util.Map<String, Object> msg = new java.util.HashMap<>();
        msg.put("event", eventType);
        msg.put("timestamp", System.currentTimeMillis());
        msg.put("data", data);
        TextMessage payload = new TextMessage(JSON.toJSONString(msg));
        for (WebSocketSession session : SESSIONS)
        {
            if (session.isOpen())
            {
                try
                {
                    session.sendMessage(payload);
                }
                catch (Exception ex)
                {
                    log.debug("跳过失效告警会话: {}", ex.getMessage());
                }
            }
        }
    }

    public static class AlertSocketHandler extends TextWebSocketHandler
    {
        @Override
        public void afterConnectionEstablished(WebSocketSession session)
        {
            SESSIONS.add(session);
        }

        @Override
        public void afterConnectionClosed(WebSocketSession session, CloseStatus status)
        {
            SESSIONS.remove(session);
        }
    }
}
