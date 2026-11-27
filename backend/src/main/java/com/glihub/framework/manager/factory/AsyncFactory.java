package com.glihub.framework.manager.factory;

import java.util.TimerTask;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import com.glihub.common.utils.LogUtils;
import com.glihub.common.utils.ServletUtils;
import com.glihub.common.utils.ip.AddressUtils;
import com.glihub.common.utils.ip.IpUtils;
import eu.bitwalker.useragentutils.UserAgent;

/**
 * 异步日志工厂（输出登录审计至 SLF4J 日志）
 *
 * @author glihub
 */
public class AsyncFactory
{
    private static final Logger sys_user_logger = LoggerFactory.getLogger("sys-user");

    /**
     * 记录登录审计信息
     *
     * @param username 用户名
     * @param status 状态
     * @param message 消息
     * @param args 列表
     * @return 任务task
     */
    public static TimerTask recordLogininfor(final String username, final String status, final String message,
            final Object... args)
    {
        final UserAgent userAgent = UserAgent.parseUserAgentString(ServletUtils.getRequest().getHeader("User-Agent"));
        final String ip = IpUtils.getIpAddr();
        return new TimerTask()
        {
            @Override
            public void run()
            {
                String address = AddressUtils.getRealAddressByIP(ip);
                String os = userAgent.getOperatingSystem().getName();
                String browser = userAgent.getBrowser().getName();
                StringBuilder s = new StringBuilder();
                s.append(LogUtils.getBlock(ip));
                s.append(address);
                s.append(LogUtils.getBlock(username));
                s.append(LogUtils.getBlock(status));
                s.append(LogUtils.getBlock(browser + "/" + os));
                s.append(LogUtils.getBlock(message));
                sys_user_logger.info(s.toString(), args);
            }
        };
    }
}
