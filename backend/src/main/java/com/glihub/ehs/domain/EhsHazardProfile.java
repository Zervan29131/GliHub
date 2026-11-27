package com.glihub.ehs.domain;

import java.math.BigDecimal;
import com.glihub.common.core.domain.BaseEntity;

/**
 * 重大危险源全息档案与厂区平面坐标实体 ehs_hazard_profile
 */
public class EhsHazardProfile extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long hazardId;
    private String hazardCode;
    private String hazardName;
    private String placeType;
    private Long deptId;
    private String deptName;
    private String leader;
    private String phone;
    private String relatedEquipIds;
    private String chemicalName;
    private String casNo;
    private BigDecimal criticalQtyTon;
    private BigDecimal actualQtyTon;
    private BigDecimal rIndex;
    private String majorHazardGrade;
    private BigDecimal dowMf;
    private BigDecimal combustionHeatKj;
    private BigDecimal mapX;
    private BigDecimal mapY;
    private Integer onDutyCount;
    private String riskLevel;
    private String physicochemicalProps;
    private String emergencyMeasures;
    private String ppeRequirements;
    private String status;

    public Long getHazardId() { return hazardId; }
    public void setHazardId(Long hazardId) { this.hazardId = hazardId; }

    public String getHazardCode() { return hazardCode; }
    public void setHazardCode(String hazardCode) { this.hazardCode = hazardCode; }

    public String getHazardName() { return hazardName; }
    public void setHazardName(String hazardName) { this.hazardName = hazardName; }

    public String getPlaceType() { return placeType; }
    public void setPlaceType(String placeType) { this.placeType = placeType; }

    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }

    public String getDeptName() { return deptName; }
    public void setDeptName(String deptName) { this.deptName = deptName; }

    public String getLeader() { return leader; }
    public void setLeader(String leader) { this.leader = leader; }

    public String getPhone() { return phone; }
    public void setPhone(String phone) { this.phone = phone; }

    public String getRelatedEquipIds() { return relatedEquipIds; }
    public void setRelatedEquipIds(String relatedEquipIds) { this.relatedEquipIds = relatedEquipIds; }

    public String getChemicalName() { return chemicalName; }
    public void setChemicalName(String chemicalName) { this.chemicalName = chemicalName; }

    public String getCasNo() { return casNo; }
    public void setCasNo(String casNo) { this.casNo = casNo; }

    public BigDecimal getCriticalQtyTon() { return criticalQtyTon; }
    public void setCriticalQtyTon(BigDecimal criticalQtyTon) { this.criticalQtyTon = criticalQtyTon; }

    public BigDecimal getActualQtyTon() { return actualQtyTon; }
    public void setActualQtyTon(BigDecimal actualQtyTon) { this.actualQtyTon = actualQtyTon; }

    public BigDecimal getRIndex() { return rIndex; }
    public void setRIndex(BigDecimal rIndex) { this.rIndex = rIndex; }

    public String getMajorHazardGrade() { return majorHazardGrade; }
    public void setMajorHazardGrade(String majorHazardGrade) { this.majorHazardGrade = majorHazardGrade; }

    public BigDecimal getDowMf() { return dowMf; }
    public void setDowMf(BigDecimal dowMf) { this.dowMf = dowMf; }

    public BigDecimal getCombustionHeatKj() { return combustionHeatKj; }
    public void setCombustionHeatKj(BigDecimal combustionHeatKj) { this.combustionHeatKj = combustionHeatKj; }

    public BigDecimal getMapX() { return mapX; }
    public void setMapX(BigDecimal mapX) { this.mapX = mapX; }

    public BigDecimal getMapY() { return mapY; }
    public void setMapY(BigDecimal mapY) { this.mapY = mapY; }

    public Integer getOnDutyCount() { return onDutyCount; }
    public void setOnDutyCount(Integer onDutyCount) { this.onDutyCount = onDutyCount; }

    public String getRiskLevel() { return riskLevel; }
    public void setRiskLevel(String riskLevel) { this.riskLevel = riskLevel; }

    public String getPhysicochemicalProps() { return physicochemicalProps; }
    public void setPhysicochemicalProps(String physicochemicalProps) { this.physicochemicalProps = physicochemicalProps; }

    public String getEmergencyMeasures() { return emergencyMeasures; }
    public void setEmergencyMeasures(String emergencyMeasures) { this.emergencyMeasures = emergencyMeasures; }

    public String getPpeRequirements() { return ppeRequirements; }
    public void setPpeRequirements(String ppeRequirements) { this.ppeRequirements = ppeRequirements; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
