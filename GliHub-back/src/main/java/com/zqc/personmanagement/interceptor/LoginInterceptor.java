package com.zqc.personmanagement.interceptor;

import org.springframework.web.servlet.HandlerInterceptor;

import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import javax.servlet.http.HttpSession;

/**
 * 登录检查
 * 1 配置好拦截器，要拦截哪些请求
 * 2 把这些配置放在容器中
 */
public class LoginInterceptor implements HandlerInterceptor {

    // 目标方法执行之前
    @Override
    public boolean preHandle(HttpServletRequest request, HttpServletResponse response, Object handler) throws Exception {
        // 登录检查逻辑
        HttpSession session = request.getSession();
        Object loginUser = session.getAttribute("loginUser");
        System.out.println(loginUser);
        if (loginUser != null) {
            // 放行
            System.out.println("放行");
            return true;
        }
        System.out.println("拦截");
        // 拦截住,未登录，跳转到登录页
        session.setAttribute("msg", "请先登录！");
        request.getRequestDispatcher("/").forward(request, response);
        return false;
    }
}
