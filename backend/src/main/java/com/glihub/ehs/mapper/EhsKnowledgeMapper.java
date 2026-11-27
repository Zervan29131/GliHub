package com.glihub.ehs.mapper;

import java.util.List;
import org.apache.ibatis.annotations.Param;
import com.glihub.ehs.domain.EhsKbChunk;
import com.glihub.ehs.domain.EhsKbDocument;

/**
 * EHS 法规标准向量知识库 Mapper（含 ai-service 离线时 SQL 全文检索降级支撑）
 */
public interface EhsKnowledgeMapper
{
    List<EhsKbDocument> selectDocList(EhsKbDocument query);

    EhsKbDocument selectDocById(@Param("docId") Long docId);

    List<EhsKbChunk> selectChunksByDocId(@Param("docId") Long docId);

    List<EhsKbChunk> searchChunksFallback(
            @Param("keyword") String keyword,
            @Param("placeType") String placeType,
            @Param("limit") int limit);

    int insertDocFallback(EhsKbDocument doc);

    int insertChunkFallback(EhsKbChunk chunk);

    int deleteDocById(@Param("docId") Long docId);
}
