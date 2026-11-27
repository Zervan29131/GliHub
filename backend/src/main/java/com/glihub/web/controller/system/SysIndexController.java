package com.glihub.web.controller.system;

import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.utils.StringUtils;

/**
 * 后端服务健康提示接口
 *
 * @author glihub
 */
@RestController
public class SysIndexController
{
    @Autowired
    private GliHubConfig gliHubConfig;

    @RequestMapping("/")
    public String index()
    {
        return StringUtils.format("{} 安全评价与安全信息管理系统后端服务运行中（版本：v{}），请通过前端地址访问。",
                gliHubConfig.getName(), gliHubConfig.getVersion());
    }
}
