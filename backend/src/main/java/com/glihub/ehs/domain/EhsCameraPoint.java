package com.glihub.ehs.domain;

import java.math.BigDecimal;
import com.glihub.common.core.domain.BaseEntity;

/**
 * 厂区视觉监控点位实体 ehs_camera_point
 */
public class EhsCameraPoint extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long pointId;
    private String pointCode;
    private String pointName;
    private String placeType;
    private Long deptId;
    private String deptName;
    private Long hazardId;
    private String hazardName;
    private Long defaultModelId;
    private String defaultModelCode;
    private String streamProtocol;
    private String streamUrl;
    private BigDecimal mapX;
    private BigDecimal mapY;
    private String status;

    public Long getPointId() { return pointId; }
    public void setPointId(Long pointId) { this.pointId = pointId; }

    public String getPointCode() { return pointCode; }
    public void setPointCode(String pointCode) { this.pointCode = pointCode; }

    public String getPointName() { return pointName; }
    public void setPointName(String pointName) { this.pointName = pointName; }

    public String getPlaceType() { return placeType; }
    public void setPlaceType(String placeType) { this.placeType = placeType; }

    public Long getDeptId() { return deptId; }
    public void setDeptId(Long deptId) { this.deptId = deptId; }

    public String getDeptName() { return deptName; }
    public void setDeptName(String deptName) { this.deptName = deptName; }

    public Long getHazardId() { return hazardId; }
    public void setHazardId(Long hazardId) { this.hazardId = hazardId; }

    public String getHazardName() { return hazardName; }
    public void setHazardName(String hazardName) { this.hazardName = hazardName; }

    public Long getDefaultModelId() { return defaultModelId; }
    public void setDefaultModelId(Long defaultModelId) { this.defaultModelId = defaultModelId; }

    public String getDefaultModelCode() { return defaultModelCode; }
    public void setDefaultModelCode(String defaultModelCode) { this.defaultModelCode = defaultModelCode; }

    public String getStreamProtocol() { return streamProtocol; }
    public void setStreamProtocol(String streamProtocol) { this.streamProtocol = streamProtocol; }

    public String getStreamUrl() { return streamUrl; }
    public void setStreamUrl(String streamUrl) { this.streamUrl = streamUrl; }

    public BigDecimal getMapX() { return mapX; }
    public void setMapX(BigDecimal mapX) { this.mapX = mapX; }

    public BigDecimal getMapY() { return mapY; }
    public void setMapY(BigDecimal mapY) { this.mapY = mapY; }

    public String getStatus() { return status; }
    public void setStatus(String status) { this.status = status; }
}
