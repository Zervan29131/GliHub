package com.glihub;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;

@SpringBootApplication
public class GliHubApplication
{
    public static void main(String[] args)
    {
        SpringApplication.run(GliHubApplication.class, args);
        System.out.println("GliHub 3.0 端云协同 AI 工业安全风控平台中台启动成功");
    }
}
