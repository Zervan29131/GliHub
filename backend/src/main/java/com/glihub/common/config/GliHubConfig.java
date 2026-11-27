package com.glihub.common.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

/**
 * GliHub 全局项目配置
 *
 * @author glihub
 */
@Component
@ConfigurationProperties(prefix = "glihub")
public class GliHubConfig
{
    /** 项目名称 */
    private String name;

    /** 版本 */
    private String version;

    /** 版权年份 */
    private String copyrightYear;

    /** 上传路径 */
    private static String profile;

    /** 获取地址开关 */
    private static boolean addressEnabled;

    /** 验证码类型 */
    private static String captchaType;

    /** FastAPI AI 微服务基础 URL */
    private static String aiServiceUrl = "http://127.0.0.1:8090";

    /** AI 输出目录 */
    private static String aiOutputDir = "../ai-service/outputs";

    /** 示例测试图像目录 */
    private static String sampleImageDir = "../yolov5target-main/data/images";

    /** AI 请求超时时间(ms) */
    private static int aiTimeoutMs = 35000;

    public String getName()
    {
        return name;
    }

    public void setName(String name)
    {
        this.name = name;
    }

    public String getVersion()
    {
        return version;
    }

    public void setVersion(String version)
    {
        this.version = version;
    }

    public String getCopyrightYear()
    {
        return copyrightYear;
    }

    public void setCopyrightYear(String copyrightYear)
    {
        this.copyrightYear = copyrightYear;
    }

    public static String getProfile()
    {
        return profile;
    }

    public void setProfile(String profile)
    {
        GliHubConfig.profile = profile;
    }

    public static boolean isAddressEnabled()
    {
        return addressEnabled;
    }

    public void setAddressEnabled(boolean addressEnabled)
    {
        GliHubConfig.addressEnabled = addressEnabled;
    }

    public static String getCaptchaType()
    {
        return captchaType;
    }

    public void setCaptchaType(String captchaType)
    {
        GliHubConfig.captchaType = captchaType;
    }

    public static String getAiServiceUrl()
    {
        return aiServiceUrl;
    }

    public void setAiServiceUrl(String aiServiceUrl)
    {
        GliHubConfig.aiServiceUrl = aiServiceUrl;
    }

    public static String getAiOutputDir()
    {
        return aiOutputDir;
    }

    public void setAiOutputDir(String aiOutputDir)
    {
        GliHubConfig.aiOutputDir = aiOutputDir;
    }

    public static String getSampleImageDir()
    {
        return sampleImageDir;
    }

    public void setSampleImageDir(String sampleImageDir)
    {
        GliHubConfig.sampleImageDir = sampleImageDir;
    }

    public static int getAiTimeoutMs()
    {
        return aiTimeoutMs;
    }

    public void setAiTimeoutMs(int aiTimeoutMs)
    {
        GliHubConfig.aiTimeoutMs = aiTimeoutMs;
    }

    public static String getImportPath()
    {
        return getProfile() + "/import";
    }

    public static String getAvatarPath()
    {
        return getProfile() + "/avatar";
    }

    public static String getDownloadPath()
    {
        return getProfile() + "/download/";
    }

    public static String getUploadPath()
    {
        return getProfile() + "/upload";
    }
}
