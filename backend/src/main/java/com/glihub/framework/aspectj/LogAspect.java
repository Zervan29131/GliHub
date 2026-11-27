package com.glihub.framework.aspectj;

import org.aspectj.lang.JoinPoint;
import org.aspectj.lang.annotation.AfterReturning;
import org.aspectj.lang.annotation.AfterThrowing;
import org.aspectj.lang.annotation.Aspect;
import org.aspectj.lang.annotation.Before;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.core.NamedThreadLocal;
import org.springframework.stereotype.Component;
import com.glihub.common.annotation.Log;
import com.glihub.common.core.domain.model.LoginUser;
import com.glihub.common.utils.SecurityUtils;
import com.glihub.common.utils.ServletUtils;
import com.glihub.common.utils.ip.IpUtils;

/**
 * 操作审计日志切面（输出至 SLF4J 日志文件，无需持久化监控表）
 *
 * @author glihub
 */
@Aspect
@Component
public class LogAspect
{
    private static final Logger log = LoggerFactory.getLogger("sys-user");

    /** 计算操作消耗时间 */
    private static final ThreadLocal<Long> TIME_THREADLOCAL = new NamedThreadLocal<Long>("Cost Time");

    @Before(value = "@annotation(controllerLog)")
    public void doBefore(JoinPoint joinPoint, Log controllerLog)
    {
        TIME_THREADLOCAL.set(System.currentTimeMillis());
    }

    @AfterReturning(pointcut = "@annotation(controllerLog)", returning = "jsonResult")
    public void doAfterReturning(JoinPoint joinPoint, Log controllerLog, Object jsonResult)
    {
        handleLog(joinPoint, controllerLog, null);
    }

    @AfterThrowing(value = "@annotation(controllerLog)", throwing = "e")
    public void doAfterThrowing(JoinPoint joinPoint, Log controllerLog, Exception e)
    {
        handleLog(joinPoint, controllerLog, e);
    }

    protected void handleLog(final JoinPoint joinPoint, Log controllerLog, final Exception e)
    {
        try
        {
            LoginUser loginUser = SecurityUtils.getLoginUser();
            String username = loginUser != null ? loginUser.getUsername() : "anonymous";
            String ip = IpUtils.getIpAddr();
            String uri = ServletUtils.getRequest().getRequestURI();
            String httpMethod = ServletUtils.getRequest().getMethod();
            long costTime = System.currentTimeMillis() - TIME_THREADLOCAL.get();
            if (e != null)
            {
                log.warn("[操作异常] 模块={} 动作={} 用户={} IP={} {} {} 耗时={}ms 错误={}",
                        controllerLog.title(), controllerLog.businessType(), username, ip, httpMethod, uri, costTime, e.getMessage());
            }
            else
            {
                log.info("[操作审计] 模块={} 动作={} 用户={} IP={} {} {} 耗时={}ms",
                        controllerLog.title(), controllerLog.businessType(), username, ip, httpMethod, uri, costTime);
            }
        }
        catch (Exception exp)
        {
            log.error("记录操作日志异常: {}", exp.getMessage());
        }
        finally
        {
            TIME_THREADLOCAL.remove();
        }
    }
}
