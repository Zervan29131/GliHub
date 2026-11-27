package com.zqc.personmanagement.config;

import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import springfox.documentation.builders.PathSelectors;
import springfox.documentation.builders.RequestHandlerSelectors;
import springfox.documentation.service.ApiInfo;
import springfox.documentation.service.Contact;
import springfox.documentation.spi.DocumentationType;
import springfox.documentation.spring.web.plugins.Docket;
import springfox.documentation.swagger2.annotations.EnableSwagger2;

import java.util.ArrayList;

@Configuration
@EnableSwagger2
public class SwaggerConfig {
    // 配置Swagger的Docket实例
    @Bean
    public Docket docket() {
        return new Docket(DocumentationType.SWAGGER_2)
                .apiInfo(apiInfo())
                .groupName("新分组")
                .enable(true)   // false 关闭swagger; true 启动swagger
                .select()
                // RequestHandlerSelectors 配置要扫描接口的方式
                // basePackage() 指定要扫描的包
                // any() 扫描全部
                // none() 不扫描
                // withClassAnnotation() 扫描类上的注解  .apis(RequestHandlerSelectors.withClassAnnotation(RestController.class))
                // withMethodAnnotation() 扫描方法上的注解  .apis(RequestHandlerSelectors.withMethodAnnotation(GetMapping.class))
                .apis(RequestHandlerSelectors.basePackage("com.zqc.personmanagement.Controller"))
                .paths(PathSelectors.ant("/Controller"))  // 过滤路径
                .build();
    }

    // 配置Swagger信息——ApiInfo
    private ApiInfo apiInfo() {
        // 作者信息
        Contact contact = new Contact("小明","url","xiaoming@qq.com");
        return new ApiInfo(
                "小明的Swagger",
                "这里是描述文档",
                "1.0",
                "urn:tos",
                contact,
                "Apache 2.0",
                "http://www.apache.org/licenses/LICENSE-2.0",
                new ArrayList());
    }

    @Bean
    public Docket docket1() {
        return new Docket(DocumentationType.SWAGGER_2).groupName("A");
    }

    @Bean
    public Docket docket2() {
        return new Docket(DocumentationType.SWAGGER_2).groupName("B");
    }
}
