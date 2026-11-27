package com.zqc.personmanagement.config;

import com.zqc.personmanagement.interceptor.LoginInterceptor;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.servlet.config.annotation.InterceptorRegistry;
import org.springframework.web.servlet.config.annotation.WebMvcConfigurer;


/**
 * 1 编写一个拦截器实现HandlerInterceptor接口
 * 2 拦截器注册到容器中（实现WebMvcConfigurer的addInterceptors）
 * 3 指定拦截规则（如果拦截所有，静态资源也会被拦截）
 */
@Configuration
public class AdminWebConfig implements WebMvcConfigurer {
    @Override
    public void addInterceptors(InterceptorRegistry registry) {
        registry.addInterceptor(new LoginInterceptor())
                .addPathPatterns("/**")   // 所有请求都被拦截
                .excludePathPatterns("/", "/user/login","/css/**","/js/**","/img/**");  // 放行的请求
    }
}
