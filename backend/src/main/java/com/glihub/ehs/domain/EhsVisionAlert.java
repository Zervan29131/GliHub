package com.glihub.ehs.domain;

import com.glihub.common.core.domain.BaseEntity;

/**
 * AI 视觉检测与 VLM 二次复核告警实体 ehs_vision_alert
 */
public class EhsVisionAlert extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long alertId;
    private String alertNo;
    private Long pointId;
    private String pointName;
    private Long deptId;
    private String deptName;
    private String placeType;
    private String modelCode;
    private String promptText;
    private String rawImageUrl;
    private String annotatedImageUrl;
    private String detectionsJson;
    private Integer inferenceMs;
    private Boolean vlmReviewed;
    private String vlmModel;
    private Boolean isRealHazard;
    private String violationType;
    private String severity;
    private String vlmDescription;
    private String vlmSuggestion;
    private String citedLawsJson;
    private String handleStatus;
    private Long orderId;

    public Long getAlertId() { return alertId; }
    public void setAlertId(Long alertId) { this.alertId = alertId; }

    public String getAlertNo() { return alertNo; }
    public void setAlertNo(String alertNo) { this.alertNo = alertNo; }

    public Long getPointId() { return pointId; }
    public void setPointId(Long pointId) { this.pointId = pointId; }

    public String getPointName() { return pointName; }
    public void setPointName(String pointName) { this.pointName = pointName; }

    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }

    public String getDeptName() { return deptName; }
    public void setDeptName(String deptName) { this.deptName = deptName; }

    public String getPlaceType() { return placeType; }
    public void setPlaceType(String placeType) { this.placeType = placeType; }

    public String getModelCode() { return modelCode; }
    public void setModelCode(String modelCode) { this.modelCode = modelCode; }

    public String getPromptText() { return promptText; }
    public void setPromptText(String promptText) { this.promptText = promptText; }

    public String getRawImageUrl() { return rawImageUrl; }
    public void setRawImageUrl(String rawImageUrl) { this.rawImageUrl = rawImageUrl; }

    public String getAnnotatedImageUrl() { return annotatedImageUrl; }
    public void setAnnotatedImageUrl(String annotatedImageUrl) { this.annotatedImageUrl = annotatedImageUrl; }

    public String getDetectionsJson() { return detectionsJson; }
    public void setDetectionsJson(String detectionsJson) { this.detectionsJson = detectionsJson; }

    public Integer getInferenceMs() { return inferenceMs; }
    public void setInferenceMs(Integer inferenceMs) { this.inferenceMs = inferenceMs; }

    public Boolean getVlmReviewed() { return vlmReviewed; }
    public void setVlmReviewed(Boolean vlmReviewed) { this.vlmReviewed = vlmReviewed; }

    public String getVlmModel() { return vlmModel; }
    public void setVlmModel(String vlmModel) { this.vlmModel = vlmModel; }

    public Boolean getIsRealHazard() { return isRealHazard; }
    public void setIsRealHazard(Boolean isRealHazard) { this.isRealHazard = isRealHazard; }

    public String getViolationType() { return violationType; }
    public void setViolationType(String violationType) { this.violationType = violationType; }

    public String getSeverity() { return severity; }
    public void setSeverity(String severity) { this.severity = severity; }

    public String getVlmDescription() { return vlmDescription; }
    public void setVlmDescription(String vlmDescription) { this.vlmDescription = vlmDescription; }

    public String getVlmSuggestion() { return vlmSuggestion; }
    public void setVlmSuggestion(String vlmSuggestion) { this.vlmSuggestion = vlmSuggestion; }

    public String getCitedLawsJson() { return citedLawsJson; }
    public void setCitedLawsJson(String citedLawsJson) { this.citedLawsJson = citedLawsJson; }

    public String getHandleStatus() { return handleStatus; }
    public void setHandleStatus(String handleStatus) { this.handleStatus = handleStatus; }

    public Long getOrderId() { return orderId; }
    public void setOrderId(Long orderId) { this.orderId = orderId; }
}
