package com.zqc.personmanagement.Controller;

import com.zqc.personmanagement.pojo.User;
import io.swagger.annotations.ApiOperation;
import io.swagger.annotations.ApiParam;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
public class SwaggerController {

    @ApiOperation("User的控制类")
    // 只要接口中，返回值中存在实体类，就会被扫描到Swagger内
    @PostMapping(value = "/user")
    public User user(@ApiParam("用户名") String name) {
        return new User();
    }
}
