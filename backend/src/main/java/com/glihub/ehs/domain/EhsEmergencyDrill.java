package com.glihub.ehs.domain;

import java.math.BigDecimal;
import com.glihub.common.core.domain.BaseEntity;

/**
 * 事故情景智能推演与应急行动卡实体 ehs_emergency_drill
 */
public class EhsEmergencyDrill extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long drillId;
    private String drillNo;
    private String triggerType;
    private Long alertId;
    private Long hazardId;
    private String hazardName;
    private String accidentType;
    private BigDecimal leakMassKg;
    private String windDirection;
    private BigDecimal windSpeedMs;
    private BigDecimal tntEquivalentKg;
    private BigDecimal r1DeathM;
    private BigDecimal r2SeriousM;
    private BigDecimal r3MinorM;
    private BigDecimal r4PropertyM;
    private String affectedEquipJson;
    private Integer affectedStaffCount;
    private String actionCardMarkdown;

    public Long getDrillId() { return drillId; }
    public void setDrillId(Long drillId) { this.drillId = drillId; }

    public String getDrillNo() { return drillNo; }
    public void setDrillNo(String drillNo) { this.drillNo = drillNo; }

    public String getTriggerType() { return triggerType; }
    public void setTriggerType(String triggerType) { this.triggerType = triggerType; }

    public Long getAlertId() { return alertId; }
    public void setAlertId(Long alertId) { this.alertId = alertId; }

    public Long getHazardId() { return hazardId; }
    public void setHazardId(Long hazardId) { this.hazardId = hazardId; }

    public String getHazardName() { return hazardName; }
    public void setHazardName(String hazardName) { this.hazardName = hazardName; }

    public String getAccidentType() { return accidentType; }
    public void setAccidentType(String accidentType) { this.accidentType = accidentType; }

    public BigDecimal getLeakMassKg() { return leakMassKg; }
    public void setLeakMassKg(BigDecimal leakMassKg) { this.leakMassKg = leakMassKg; }

    public String getWindDirection() { return windDirection; }
    public void setWindDirection(String windDirection) { this.windDirection = windDirection; }

    public BigDecimal getWindSpeedMs() { return windSpeedMs; }
    public void setWindSpeedMs(BigDecimal windSpeedMs) { this.windSpeedMs = windSpeedMs; }

    public BigDecimal getTntEquivalentKg() { return tntEquivalentKg; }
    public void setTntEquivalentKg(BigDecimal tntEquivalentKg) { this.tntEquivalentKg = tntEquivalentKg; }

    public BigDecimal getR1DeathM() { return r1DeathM; }
    public void setR1DeathM(BigDecimal r1DeathM) { this.r1DeathM = r1DeathM; }

    public BigDecimal getR2SeriousM() { return r2SeriousM; }
    public void setR2SeriousM(BigDecimal r2SeriousM) { this.r2SeriousM = r2SeriousM; }

    public BigDecimal getR3MinorM() { return r3MinorM; }
    public void setR3MinorM(BigDecimal r3MinorM) { this.r3MinorM = r3MinorM; }

    public BigDecimal getR4PropertyM() { return r4PropertyM; }
    public void setR4PropertyM(BigDecimal r4PropertyM) { this.r4PropertyM = r4PropertyM; }

    public String getAffectedEquipJson() { return affectedEquipJson; }
    public void setAffectedEquipJson(String affectedEquipJson) { this.affectedEquipJson = affectedEquipJson; }

    public Integer getAffectedStaffCount() { return affectedStaffCount; }
    public void setAffectedStaffCount(Integer affectedStaffCount) { this.affectedStaffCount = affectedStaffCount; }

    public String getActionCardMarkdown() { return actionCardMarkdown; }
    public void setActionCardMarkdown(String actionCardMarkdown) { this.actionCardMarkdown = actionCardMarkdown; }
}
