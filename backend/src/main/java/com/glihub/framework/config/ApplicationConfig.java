package com.glihub.framework.config;

import java.util.TimeZone;
import jakarta.annotation.PostConstruct;
import org.mybatis.spring.annotation.MapperScan;
import org.springframework.context.annotation.Configuration;
import org.springframework.context.annotation.EnableAspectJAutoProxy;

@Configuration
@EnableAspectJAutoProxy(exposeProxy = true)
@MapperScan("com.glihub.**.mapper")
public class ApplicationConfig
{
    @PostConstruct
    public void initDefaultTimeZone()
    {
        TimeZone.setDefault(TimeZone.getDefault());
    }
}
