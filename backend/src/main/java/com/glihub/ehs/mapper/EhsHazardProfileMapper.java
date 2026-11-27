package com.glihub.ehs.mapper;

import java.util.List;
import org.apache.ibatis.annotations.Param;
import com.glihub.ehs.domain.EhsEmergencyDrill;
import com.glihub.ehs.domain.EhsHazardProfile;

/**
 * 重大危险源全息档案与事故推演 Mapper
 */
public interface EhsHazardProfileMapper
{
    List<EhsHazardProfile> selectProfileList(EhsHazardProfile query);

    EhsHazardProfile selectProfileById(@Param("hazardId") Long hazardId);

    int insertProfile(EhsHazardProfile profile);

    int updateProfile(EhsHazardProfile profile);

    int deleteProfileById(@Param("hazardId") Long hazardId);

    List<EhsEmergencyDrill> selectDrillList(EhsEmergencyDrill query);

    int insertDrill(EhsEmergencyDrill drill);
}
