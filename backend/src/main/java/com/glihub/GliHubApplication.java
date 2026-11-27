package com.glihub;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.boot.autoconfigure.jdbc.DataSourceAutoConfiguration;

/**
 * GliHub 系统启动程序
 *
 * @author glihub
 */
@SpringBootApplication(exclude = { DataSourceAutoConfiguration.class })
public class GliHubApplication
{
    public static void main(String[] args)
    {
        SpringApplication.run(GliHubApplication.class, args);
        System.out.println("GliHub 安全评价与安全信息管理系统启动成功");
    }
}
