package com.glihub.ehs.domain;

import java.util.Date;
import com.fasterxml.jackson.annotation.JsonFormat;
import com.glihub.common.core.domain.BaseEntity;

/**
 * 隐患排查治理闭环工单实体 ehs_hazard_order
 */
public class EhsHazardOrder extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long orderId;
    private String orderNo;
    private String sourceType;
    private Long alertId;
    private Long deptId;
    private String deptName;
    private String placeType;
    private Long hazardId;
    private String hazardName;
    private Long equipId;
    private String equipName;
    private String hazardTitle;
    private String hazardCategory;
    private String riskLevel;
    private String legalBasis;
    private String rectifyMeasure;
    private Long responsibleUserId;
    private String responsibleName;
    @JsonFormat(pattern = "yyyy-MM-dd HH:mm:ss")
    private Date deadline;
    private String rectifyImageUrl;
    private String rectifyNote;
    private Boolean aiRecheckPassed;
    private String aiRecheckComment;
    private String status;

    public Long getOrderId() { return orderId; }
    public void setOrderId(Long orderId) { this.orderId = orderId; }

    public String getOrderNo() { return orderNo; }
    public void setOrderNo(String orderNo) { this.orderNo = orderNo; }

    public String getSourceType() { return sourceType; }
    public void setSourceType(String sourceType) { this.sourceType = sourceType; }

    public Long getAlertId() { return alertId; }
    public void setAlertId(Long alertId) { this.alertId = alertId; }

    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }

    public String getDeptName() { return deptName; }
    public void setDeptName(String deptName) { this.deptName = deptName; }

    public String getPlaceType() { return placeType; }
    public void setPlaceType(String placeType) { this.placeType = placeType; }

    public Long getHazardId() { return hazardId; }
    public void setHazardId(Long hazardId) { this.hazardId = hazardId; }

    public String getHazardName() { return hazardName; }
    public void setHazardName(String hazardName) { this.hazardName = hazardName; }

    public Long getEquipId() { return equipId; }
    public void setEquipId(Long equipId) { this.equipId = equipId; }

    public String getEquipName() { return equipName; }
    public void setEquipName(String equipName) { this.equipName = equipName; }

    public String getHazardTitle() { return hazardTitle; }
    public void setHazardTitle(String hazardTitle) { this.hazardTitle = hazardTitle; }

    public String getHazardCategory() { return hazardCategory; }
    public void setHazardCategory(String hazardCategory) { this.hazardCategory = hazardCategory; }

    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }

    public String getLegalBasis() { return legalBasis; }
    public void setLegalBasis(String legalBasis) { this.legalBasis = legalBasis; }

    public String getRectifyMeasure() { return rectifyMeasure; }
    public void setRectifyMeasure(String rectifyMeasure) { this.rectifyMeasure = rectifyMeasure; }

    public Long getResponsibleUserId() { return responsibleUserId; }
    public void setResponsibleUserId(Long responsibleUserId) { this.responsibleUserId = responsibleUserId; }

    public String getResponsibleName() { return responsibleName; }
    public void setResponsibleName(String responsibleName) { this.responsibleName = responsibleName; }

    public Date getDeadline() { return deadline; }
    public void setDeadline(Date deadline) { this.deadline = deadline; }

    public String getRectifyImageUrl() { return rectifyImageUrl; }
    public void setRectifyImageUrl(String rectifyImageUrl) { this.rectifyImageUrl = rectifyImageUrl; }

    public String getRectifyNote() { return rectifyNote; }
    public void setRectifyNote(String rectifyNote) { this.rectifyNote = rectifyNote; }

    public Boolean getAiRecheckPassed() { return aiRecheckPassed; }
    public void setAiRecheckPassed(Boolean aiRecheckPassed) { this.aiRecheckPassed = aiRecheckPassed; }

    public String getAiRecheckComment() { return aiRecheckComment; }
    public void setAiRecheckComment(String aiRecheckComment) { this.aiRecheckComment = aiRecheckComment; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
