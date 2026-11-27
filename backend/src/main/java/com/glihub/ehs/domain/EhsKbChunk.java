package com.glihub.ehs.domain;

import com.glihub.common.core.domain.BaseEntity;

/**
 * EHS 安全知识库条款切片实体 ehs_kb_chunk
 */
public class EhsKbChunk extends BaseEntity
{
    private static final long serialVersionUID = 1L;

    private Long chunkId;
    private Long docId;
    private String docTitle;
    private String docCategory;
    private String standardCode;
    private Integer chunkIndex;
    private String clauseNo;
    private String chunkText;
    private String applicablePlaces;
    private String hazardTags;

    public Long getChunkId() { return chunkId; }
    public void setChunkId(Long chunkId) { this.chunkId = chunkId; }

    public Long getDocId() { return docId; }
    public void setDocId(Long docId) { this.docId = docId; }

    public String getDocTitle() { return docTitle; }
    public void setDocTitle(String docTitle) { this.docTitle = docTitle; }

    public String getDocCategory() { return docCategory; }
    public void setDocCategory(String docCategory) { this.docCategory = docCategory; }

    public String getStandardCode() { return standardCode; }
    public void setStandardCode(String standardCode) { this.standardCode = standardCode; }

    public Integer getChunkIndex() { return chunkIndex; }
    public void setChunkIndex(Integer chunkIndex) { this.chunkIndex = chunkIndex; }

    public String getClauseNo() { return clauseNo; }
    public void setClauseNo(String clauseNo) { this.clauseNo = clauseNo; }

    public String getChunkText() { return chunkText; }
    public void setChunkText(String chunkText) { this.chunkText = chunkText; }

    public String getApplicablePlaces() { return applicablePlaces; }
    public void setApplicablePlaces(String applicablePlaces) { this.applicablePlaces = applicablePlaces; }

    public String getHazardTags() { return hazardTags; }
    public void setHazardTags(String hazardTags) { this.hazardTags = hazardTags; }
}
