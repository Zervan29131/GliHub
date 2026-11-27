package com.glihub.framework.config;

import java.io.File;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;
import org.springframework.web.filter.CorsFilter;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.ResourceHandlerRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.constant.Constants;
import com.glihub.framework.interceptor.RepeatSubmitInterceptor;

@Configuration
public class ResourcesConfig implements WebMvcConfigurer
{
    @Autowired
    private RepeatSubmitInterceptor repeatSubmitInterceptor;

    @Override
    public void addResourceHandlers(ResourceHandlerRegistry registry)
    {
        String profilePath = new File(GliHubConfig.getProfile()).getAbsolutePath() + File.separator;
        registry.addResourceHandler(Constants.RESOURCE_PREFIX + "/**")
                .addResourceLocations("file:" + profilePath);

        String aiOutPath = new File(GliHubConfig.getAiOutputDir()).getAbsolutePath() + File.separator;
        registry.addResourceHandler("/ai-outputs/**")
                .addResourceLocations("file:" + aiOutPath);

        String samplePath = new File(GliHubConfig.getSampleImageDir()).getAbsolutePath() + File.separator;
        registry.addResourceHandler("/sample-images/**")
                .addResourceLocations("file:" + samplePath);

        String edgeSnapsPath = new File(GliHubConfig.getEdgeSnapsDir()).getAbsolutePath() + File.separator;
        registry.addResourceHandler("/edge-snaps/**")
                .addResourceLocations("file:" + edgeSnapsPath);
    }

    @Override
    public void addInterceptors(InterceptorRegistry registry)
    {
        registry.addInterceptor(repeatSubmitInterceptor).addPathPatterns("/**")
                .excludePathPatterns("/ehs/kb/chat/stream", "/ehs/vision/detect/**", "/ehs/edge/**");
    }

    @Bean
    public CorsFilter corsFilter()
    {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowCredentials(true);
        config.addAllowedOriginPattern("*");
        config.addAllowedHeader("*");
        config.addAllowedMethod("*");
        config.setMaxAge(1800L);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/**", config);
        return new CorsFilter(source);
    }
}
