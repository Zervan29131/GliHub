package com.glihub.ehs.mapper;

import java.util.List;
import java.util.Map;
import org.apache.ibatis.annotations.Param;
import com.glihub.ehs.domain.EhsCameraPoint;
import com.glihub.ehs.domain.EhsVisionAlert;
import com.glihub.ehs.domain.EhsVisionModel;

/**
 * 视觉模型、监控点位与告警 Mapper
 */
public interface EhsVisionMapper
{
    List<EhsVisionModel> selectModelList(EhsVisionModel query);

    EhsVisionModel selectModelByCode(@Param("modelCode") String modelCode);

    int insertModel(EhsVisionModel model);

    int updateModel(EhsVisionModel model);

    int clearDefaultModels();

    int deleteModelById(@Param("modelId") Long modelId);

    List<EhsCameraPoint> selectCameraPointList(EhsCameraPoint query);

    EhsCameraPoint selectCameraPointById(@Param("pointId") Long pointId);

    List<EhsVisionAlert> selectAlertList(EhsVisionAlert query);

    EhsVisionAlert selectAlertById(@Param("alertId") Long alertId);

    int insertAlert(EhsVisionAlert alert);

    int updateAlertStatus(EhsVisionAlert alert);

    int countRecentRealAlertsByDept(@Param("deptId") Long deptId);

    List<Map<String, Object>> selectAlertCountBySeverity();
}
