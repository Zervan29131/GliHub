package com.glihub.framework.config;

import io.swagger.v3.oas.models.OpenAPI;
import io.swagger.v3.oas.models.info.Info;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class OpenApiConfig
{
    @Bean
    public OpenAPI glihubOpenApi()
    {
        return new OpenAPI()
                .info(new Info()
                        .title("GliHub 3.0 AI-EHS 端云协同智能安全风控平台 API")
                        .version("3.0.0")
                        .description("涵盖确定性安全评价(Dow/LEC/TNT/SCL)、边缘计算网关(/ehs/edge/*)、7大AI选装插件管理与隐患治理全闭环 OpenAPI 3.1 契约。"));
    }
}
