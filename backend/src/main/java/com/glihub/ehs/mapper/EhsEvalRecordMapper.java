package com.glihub.ehs.mapper;

import java.util.List;
import org.apache.ibatis.annotations.Param;
import com.glihub.ehs.domain.EhsEvalRecord;

/**
 * 动态安全评价记录与 AI 报告归档 Mapper
 */
public interface EhsEvalRecordMapper
{
    List<EhsEvalRecord> selectRecordList(EhsEvalRecord query);

    EhsEvalRecord selectRecordById(@Param("evalId") Long evalId);

    int insertRecord(EhsEvalRecord record);
}
