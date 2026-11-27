package com.glihub.web.controller.ehs;

import java.io.File;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.constant.Constants;
import com.glihub.common.core.controller.BaseController;
import com.glihub.common.core.domain.AjaxResult;
import com.glihub.common.core.page.TableDataInfo;
import com.glihub.common.utils.file.FileUploadUtils;
import com.glihub.ehs.client.AiServiceClient;
import com.glihub.ehs.domain.EhsCameraPoint;
import com.glihub.ehs.domain.EhsHazardOrder;
import com.glihub.ehs.domain.EhsVisionAlert;
import com.glihub.ehs.domain.EhsVisionModel;
import com.glihub.ehs.mapper.EhsVisionMapper;
import com.glihub.ehs.service.EhsClosedLoopService;

@RestController
@RequestMapping("/ehs")
public class EhsVisionController extends BaseController
{
    @Autowired
    private EhsClosedLoopService closedLoopService;
    @Autowired
    private EhsVisionMapper visionMapper;
    @Autowired
    private AiServiceClient aiClient;

    @GetMapping("/dashboard/overview")
    public AjaxResult dashboardOverview()
    {
        return success(closedLoopService.buildCommandCenterOverview());
    }

    @GetMapping("/vision/models")
    public AjaxResult listModels(EhsVisionModel query)
    {
        return success(closedLoopService.listVisionModels(query));
    }

    @PostMapping("/vision/models")
    public AjaxResult saveNewModel(@RequestBody EhsVisionModel model)
    {
        model.setCreateBy(getUsername());
        if (Boolean.TRUE.equals(model.getIsDefault()))
        {
            visionMapper.clearDefaultModels();
        }
        visionMapper.insertModel(model);
        if ("yolov5_local".equals(model.getAdapterType()) && model.getWeightsPath() != null)
        {
            Map<String, Object> reg = new HashMap<>();
            reg.put("model_code", model.getModelCode());
            reg.put("weights_path", model.getWeightsPath());
            aiClient.postJsonWithFallback("/api/v1/vision/register", reg, new com.alibaba.fastjson2.JSONObject());
        }
        return success(model);
    }

    @PutMapping("/vision/models")
    public AjaxResult editModel(@RequestBody EhsVisionModel model)
    {
        if (Boolean.TRUE.equals(model.getIsDefault()))
        {
            visionMapper.clearDefaultModels();
        }
        return toAjax(visionMapper.updateModel(model));
    }

    @DeleteMapping("/vision/models/{modelId}")
    public AjaxResult removeModel(@PathVariable Long modelId)
    {
        return toAjax(visionMapper.deleteModelById(modelId));
    }

    @GetMapping("/vision/points")
    public AjaxResult listPoints(EhsCameraPoint query)
    {
        return success(visionMapper.selectCameraPointList(query));
    }

    @GetMapping("/vision/samples")
    public AjaxResult builtInSamples()
    {
        List<Map<String, String>> samples = Arrays.asList(
                Map.of("title", "采油作业区-人员未佩戴安全帽抓拍", "relPath", "zidane.jpg", "url", "/sample-images/zidane.jpg", "placeType", "production"),
                Map.of("title", "生产巡检通道-安全帽混合场景抓拍", "relPath", "test/BikesHelmets172.png", "url", "/sample-images/test/BikesHelmets172.png", "placeType", "production"),
                Map.of("title", "储罐装卸外围-厂区通勤车与人员排查", "relPath", "bus.jpg", "url", "/sample-images/bus.jpg", "placeType", "storage"),
                Map.of("title", "公辅巡检通道-全员规范佩戴安全帽合规样本", "relPath", "archive/images/BikesHelmets0.png", "url", "/sample-images/archive/images/BikesHelmets0.png", "placeType", "auxiliary")
        );
        return success(samples);
    }

    @PostMapping("/vision/detect/upload")
    public AjaxResult detectUploadedImage(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "pointId", required = false) Long pointId,
            @RequestParam(value = "deptId", required = false) Long deptId,
            @RequestParam(value = "placeType", defaultValue = "production") String placeType,
            @RequestParam(value = "modelCode", defaultValue = "yolov5_helmet_local") String modelCode,
            @RequestParam(value = "promptText", required = false) String promptText,
            @RequestParam(value = "confThres", defaultValue = "0.35") Double confThres,
            @RequestParam(value = "enableVlm", defaultValue = "true") Boolean enableVlm) throws Exception
    {
        String baseUpload = GliHubConfig.getUploadPath();
        String relResourceUrl = FileUploadUtils.upload(baseUpload, file);
        String subPath = relResourceUrl.replaceFirst("^" + Constants.RESOURCE_PREFIX, "");
        File localFile = new File(GliHubConfig.getProfile(), subPath).getAbsoluteFile();

        Map<String, Object> out = closedLoopService.executeVisionAnalyze(
                localFile.getAbsolutePath(),
                relResourceUrl,
                pointId,
                deptId,
                placeType,
                modelCode,
                promptText,
                confThres,
                enableVlm,
                getUsernameSafe());
        return success(out);
    }

    @PostMapping("/vision/detect/sample")
    public AjaxResult detectSampleImage(@RequestBody Map<String, Object> body)
    {
        String sampleRel = String.valueOf(body.getOrDefault("sampleRelPath", "zidane.jpg"));
        if (sampleRel.contains(".."))
        {
            return error("非法样本路径");
        }
        File sampleFile = new File(GliHubConfig.getSampleImageDir(), sampleRel).getAbsoluteFile();
        if (!sampleFile.exists())
        {
            return error("样本图像不存在: " + sampleRel);
        }
        Long pointId = body.get("pointId") != null ? Long.valueOf(String.valueOf(body.get("pointId"))) : null;
        Long deptId = body.get("deptId") != null ? Long.valueOf(String.valueOf(body.get("deptId"))) : 103L;
        String placeType = String.valueOf(body.getOrDefault("placeType", "production"));
        String modelCode = String.valueOf(body.getOrDefault("modelCode", "yolov5_helmet_local"));
        String promptText = body.get("promptText") != null ? String.valueOf(body.get("promptText")) : null;
        Double confThres = body.get("confThres") != null ? Double.valueOf(String.valueOf(body.get("confThres"))) : 0.35;
        Boolean enableVlm = body.get("enableVlm") == null || Boolean.parseBoolean(String.valueOf(body.get("enableVlm")));

        Map<String, Object> out = closedLoopService.executeVisionAnalyze(
                sampleFile.getAbsolutePath(),
                "/sample-images/" + sampleRel,
                pointId,
                deptId,
                placeType,
                modelCode,
                promptText,
                confThres,
                enableVlm,
                getUsernameSafe());
        return success(out);
    }

    @GetMapping("/vision/alerts")
    public TableDataInfo listAlerts(EhsVisionAlert query)
    {
        startPage();
        List<EhsVisionAlert> list = visionMapper.selectAlertList(query);
        return getDataTable(list);
    }

    @PutMapping("/vision/alerts/{alertId}/convert-order")
    public AjaxResult convertAlertToOrder(@PathVariable Long alertId)
    {
        EhsHazardOrder order = closedLoopService.createOrderFromAlert(alertId, getUsernameSafe());
        return success(order);
    }

    @PutMapping("/vision/alerts/{alertId}/dismiss")
    public AjaxResult dismissAlert(@PathVariable Long alertId)
    {
        EhsVisionAlert upd = new EhsVisionAlert();
        upd.setAlertId(alertId);
        upd.setHandleStatus("DISMISSED");
        return toAjax(visionMapper.updateAlertStatus(upd));
    }

    private String getUsernameSafe()
    {
        try { return getUsername(); } catch (Exception e) { return "admin"; }
    }
}
