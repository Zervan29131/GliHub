package com.glihub.common.config;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.stereotype.Component;

@Component
@ConfigurationProperties(prefix = "glihub")
public class GliHubConfig
{
    private String name;
    private String version;
    private String copyrightYear;

    private static String profile = "../data/uploads";
    private static boolean addressEnabled;
    private static String captchaType = "math";
    private static String aiServiceUrl = "http://127.0.0.1:8090";
    private static String aiOutputDir = "../ai-service/outputs";
    private static String sampleImageDir = "../../yolov5target-main/data/images";
    private static String modelsDir = "../data/models";
    private static String edgeSnapsDir = "../data/edge_snaps";
    private static String edgeSharedToken = "glihub-edge-shared-token-v3";
    private static int aiTimeoutMs = 35000;

    public String getName() { return name; }
    public void setName(String name) { this.name = name; }

    public String getVersion() { return version; }
    public void setVersion(String version) { this.version = version; }

    public String getCopyrightYear() { return copyrightYear; }
    public void setCopyrightYear(String copyrightYear) { this.copyrightYear = copyrightYear; }

    public static String getProfile() { return profile; }
    public void setProfile(String profile) { GliHubConfig.profile = profile; }

    public static boolean isAddressEnabled() { return addressEnabled; }
    public void setAddressEnabled(boolean addressEnabled) { GliHubConfig.addressEnabled = addressEnabled; }

    public static String getCaptchaType() { return captchaType; }
    public void setCaptchaType(String captchaType) { GliHubConfig.captchaType = captchaType; }

    public static String getAiServiceUrl() { return aiServiceUrl; }
    public void setAiServiceUrl(String aiServiceUrl) { GliHubConfig.aiServiceUrl = aiServiceUrl; }

    public static String getAiOutputDir() { return resolveExistingDir(aiOutputDir, "./ai-service/outputs", "../ai-service/outputs"); }
    public void setAiOutputDir(String aiOutputDir) { GliHubConfig.aiOutputDir = aiOutputDir; }

    public static String getSampleImageDir()
    {
        return resolveExistingDir(
                sampleImageDir,
                "./yolov5target-main/data/images",
                "../yolov5target-main/data/images",
                "../../yolov5target-main/data/images",
                "./data/calib_samples",
                "../data/calib_samples"
        );
    }
    public void setSampleImageDir(String sampleImageDir) { GliHubConfig.sampleImageDir = sampleImageDir; }

    public static String getModelsDir() { return resolveExistingDir(modelsDir, "./data/models", "../data/models"); }
    public void setModelsDir(String modelsDir) { GliHubConfig.modelsDir = modelsDir; }

    public static String getEdgeSnapsDir() { return edgeSnapsDir; }
    public void setEdgeSnapsDir(String edgeSnapsDir) { GliHubConfig.edgeSnapsDir = edgeSnapsDir; }

    public static String getEdgeSharedToken() { return edgeSharedToken; }
    public void setEdgeSharedToken(String edgeSharedToken) { GliHubConfig.edgeSharedToken = edgeSharedToken; }

    public static int getAiTimeoutMs() { return aiTimeoutMs; }
    public void setAiTimeoutMs(int aiTimeoutMs) { GliHubConfig.aiTimeoutMs = aiTimeoutMs; }

    public static String getImportPath() { return getProfile() + "/import"; }
    public static String getAvatarPath() { return getProfile() + "/avatar"; }
    public static String getDownloadPath() { return getProfile() + "/download/"; }
    public static String getUploadPath() { return getProfile() + "/upload"; }

    private static String resolveExistingDir(String configured, String... fallbacks)
    {
        if (configured != null && Files.exists(Paths.get(configured)))
        {
            return configured;
        }
        for (String fb : fallbacks)
        {
            Path p = Paths.get(fb);
            if (Files.exists(p))
            {
                return fb;
            }
        }
        return configured;
    }
}
