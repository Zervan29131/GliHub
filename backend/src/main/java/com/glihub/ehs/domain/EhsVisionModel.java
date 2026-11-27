package com.glihub.ehs.domain;

import java.math.BigDecimal;
import com.glihub.common.core.domain.BaseEntity;

/**
 * 视觉与多模态检测模型注册实体 ehs_vision_model
 */
public class EhsVisionModel extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long modelId;
    private String modelCode;
    private String modelName;
    private String adapterType;
    private String taskType;
    private String weightsPath;
    private String labelsJson;
    private BigDecimal confThreshold;
    private BigDecimal iouThreshold;
    private Boolean vlmReviewEnabled;
    private BigDecimal vlmTriggerConf;
    private String applicablePlaces;
    private Boolean isDefault;
    private String status;
    /** 运行时状态（由 ai-service 健康检查合并填充） */
    private Boolean runtimeReady;
    private String runtimeMessage;

    public Long getModelId() { return modelId; }
    public void setModelId(Long modelId) { this.modelId = modelId; }

    public String getModelCode() { return modelCode; }
    public void setModelCode(String modelCode) { this.modelCode = modelCode; }

    public String getModelName() { return modelName; }
    public void setModelName(String modelName) { this.modelName = modelName; }

    public String getAdapterType() { return adapterType; }
    public void setAdapterType(String adapterType) { this.adapterType = adapterType; }

    public String getTaskType() { return taskType; }
    public void setTaskType(String taskType) { this.taskType = taskType; }

    public String getWeightsPath() { return weightsPath; }
    public void setWeightsPath(String weightsPath) { this.weightsPath = weightsPath; }

    public String getLabelsJson() { return labelsJson; }
    public void setLabelsJson(String labelsJson) { this.labelsJson = labelsJson; }

    public BigDecimal getConfThreshold() { return confThreshold; }
    public void setConfThreshold(BigDecimal confThreshold) { this.confThreshold = confThreshold; }

    public BigDecimal getIoUThreshold() { return iouThreshold; }
    public BigDecimal getIouThreshold() { return iouThreshold; }
    public void setIouThreshold(BigDecimal iouThreshold) { this.iouThreshold = iouThreshold; }

    public Boolean getVlmReviewEnabled() { return vlmReviewEnabled; }
    public void setVlmReviewEnabled(Boolean vlmReviewEnabled) { this.vlmReviewEnabled = vlmReviewEnabled; }

    public BigDecimal getVlmTriggerConf() { return vlmTriggerConf; }
    public void setVlmTriggerConf(BigDecimal vlmTriggerConf) { this.vlmTriggerConf = vlmTriggerConf; }

    public String getApplicablePlaces() { return applicablePlaces; }
    public void setApplicablePlaces(String applicablePlaces) { this.applicablePlaces = applicablePlaces; }

    public Boolean getIsDefault() { return isDefault; }
    public void setIsDefault(Boolean isDefault) { this.isDefault = isDefault; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }

    public Boolean getRuntimeReady() { return runtimeReady; }
    public void setRuntimeReady(Boolean runtimeReady) { this.runtimeReady = runtimeReady; }

    public String getRuntimeMessage() { return runtimeMessage; }
    public void setRuntimeMessage(String runtimeMessage) { this.runtimeMessage = runtimeMessage; }
}
