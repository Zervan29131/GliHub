package com.glihub.ehs.domain;

import com.glihub.common.core.domain.BaseEntity;

/**
 * 安全评价计算与 AI 报告归档实体 ehs_eval_record
 */
public class EhsEvalRecord extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long evalId;
    private String evalNo;
    private String placeType;
    private Long deptId;
    private String areaName;
    private Long hazardId;
    private String evalMethod;
    private String inputParamsJson;
    private String resultMetricsJson;
    private String riskGrade;
    private Integer dynamicAlertCount;
    private Integer openOrderCount;
    private Boolean reEvalRecommended;
    private String aiParamAdviceJson;
    private String aiReportMarkdown;
    private String evaluator;

    public Long getEvalId() { return evalId; }
    public void setEvalId(Long evalId) { this.evalId = evalId; }

    public String getEvalNo() { return evalNo; }
    public void setEvalNo(String evalNo) { this.evalNo = evalNo; }

    public String getPlaceType() { return placeType; }
    public void setPlaceType(String placeType) { this.placeType = placeType; }

    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }

    public String getAreaName() { return areaName; }
    public void setAreaName(String areaName) { this.areaName = areaName; }

    public Long getHazardId() { return hazardId; }
    public void setHazardId(Long hazardId) { this.hazardId = hazardId; }

    public String getEvalMethod() { return evalMethod; }
    public void setEvalMethod(String evalMethod) { this.evalMethod = evalMethod; }

    public String getInputParamsJson() { return inputParamsJson; }
    public void setInputParamsJson(String inputParamsJson) { this.inputParamsJson = inputParamsJson; }

    public String getResultMetricsJson() { return resultMetricsJson; }
    public void setResultMetricsJson(String resultMetricsJson) { this.resultMetricsJson = resultMetricsJson; }

    public String getRiskGrade() { return riskGrade; }
    public void setRiskGrade(String riskGrade) { this.riskGrade = riskGrade; }

    public Integer getDynamicAlertCount() { return dynamicAlertCount; }
    public void setDynamicAlertCount(Integer dynamicAlertCount) { this.dynamicAlertCount = dynamicAlertCount; }

    public Integer getOpenOrderCount() { return openOrderCount; }
    public void setOpenOrderCount(Integer openOrderCount) { this.openOrderCount = openOrderCount; }

    public Boolean getReEvalRecommended() { return reEvalRecommended; }
    public void setReEvalRecommended(Boolean reEvalRecommended) { this.reEvalRecommended = reEvalRecommended; }

    public String getAiParamAdviceJson() { return aiParamAdviceJson; }
    public void setAiParamAdviceJson(String aiParamAdviceJson) { this.aiParamAdviceJson = aiParamAdviceJson; }

    public String getAiReportMarkdown() { return aiReportMarkdown; }
    public void setAiReportMarkdown(String aiReportMarkdown) { this.aiReportMarkdown = aiReportMarkdown; }

    public String getEvaluator() { return evaluator; }
    public void setEvaluator(String evaluator) { this.evaluator = evaluator; }
}
