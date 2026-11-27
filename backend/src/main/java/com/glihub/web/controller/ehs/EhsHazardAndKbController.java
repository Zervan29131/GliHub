package com.glihub.web.controller.ehs;

import java.io.File;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.http.MediaType;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import org.springframework.web.servlet.mvc.method.annotation.SseEmitter;
import com.alibaba.fastjson2.JSON;
import com.alibaba.fastjson2.JSONObject;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.constant.Constants;
import com.glihub.common.core.controller.BaseController;
import com.glihub.common.core.domain.AjaxResult;
import com.glihub.common.core.page.TableDataInfo;
import com.glihub.common.utils.file.FileUploadUtils;
import com.glihub.ehs.client.AiServiceClient;
import com.glihub.ehs.domain.EhsEmergencyDrill;
import com.glihub.ehs.domain.EhsHazardProfile;
import com.glihub.ehs.domain.EhsKbChunk;
import com.glihub.ehs.domain.EhsKbDocument;
import com.glihub.ehs.mapper.EhsHazardProfileMapper;
import com.glihub.ehs.mapper.EhsKnowledgeMapper;
import com.glihub.ehs.service.EhsClosedLoopService;

@RestController
@RequestMapping("/ehs")
public class EhsHazardAndKbController extends BaseController
{
    @Autowired
    private EhsHazardProfileMapper profileMapper;
    @Autowired
    private EhsKnowledgeMapper knowledgeMapper;
    @Autowired
    private EhsClosedLoopService closedLoopService;
    @Autowired
    private AiServiceClient aiClient;

    // ==================== 重大危险源全息图谱与事故推演 ====================

    @GetMapping("/hazard/profiles")
    public AjaxResult listHazardProfiles(EhsHazardProfile query)
    {
        return success(profileMapper.selectProfileList(query));
    }

    @GetMapping("/hazard/{hazardId}/graph")
    public AjaxResult hazardGraph(@PathVariable Long hazardId)
    {
        return success(closedLoopService.getHazardHolographicGraph(hazardId));
    }

    @PostMapping("/hazard")
    public AjaxResult addHazard(@RequestBody EhsHazardProfile profile)
    {
        if (profile.getHazardCode() == null || profile.getHazardCode().isEmpty())
        {
            profile.setHazardCode("HZ-" + System.currentTimeMillis() % 100000);
        }
        profile.setCreateBy(resolveOperator());
        profileMapper.insertProfile(profile);
        return success(profile);
    }

    @PutMapping("/hazard")
    public AjaxResult editHazard(@RequestBody EhsHazardProfile profile)
    {
        return toAjax(profileMapper.updateProfile(profile));
    }

    @DeleteMapping("/hazard/{hazardId}")
    public AjaxResult deleteHazard(@PathVariable Long hazardId)
    {
        return toAjax(profileMapper.deleteProfileById(hazardId));
    }

    @PostMapping("/emergency/simulate")
    public AjaxResult simulateEmergency(@RequestBody Map<String, Object> body)
    {
        Long hazardId = Long.valueOf(String.valueOf(body.getOrDefault("hazardId", 1)));
        String accidentType = String.valueOf(body.getOrDefault("accidentType", "可燃介质泄漏与蒸气云爆炸"));
        double leakMassKg = Double.parseDouble(String.valueOf(body.getOrDefault("leakMassKg", 3000)));
        String windDir = String.valueOf(body.getOrDefault("windDirection", "东南风"));
        double windSpeed = Double.parseDouble(String.valueOf(body.getOrDefault("windSpeedMs", 3.2)));

        EhsEmergencyDrill drill = closedLoopService.runEmergencySimulation(
                hazardId, accidentType, leakMassKg, windDir, windSpeed, resolveOperator());
        return success(drill);
    }

    @GetMapping("/emergency/drills")
    public TableDataInfo listDrills(EhsEmergencyDrill query)
    {
        startPage();
        List<EhsEmergencyDrill> rows = profileMapper.selectDrillList(query);
        return getDataTable(rows);
    }

    // ==================== EHS 法规标准向量知识库与 SSE 合规助手 ====================

    @GetMapping("/kb/docs")
    public AjaxResult listDocs(EhsKbDocument query)
    {
        return success(knowledgeMapper.selectDocList(query));
    }

    @GetMapping("/kb/docs/{docId}/chunks")
    public AjaxResult listDocChunks(@PathVariable Long docId)
    {
        return success(knowledgeMapper.selectChunksByDocId(docId));
    }

    @PostMapping("/kb/ingest")
    public AjaxResult ingestText(@RequestBody Map<String, Object> body)
    {
        String docTitle = String.valueOf(body.getOrDefault("docTitle", "新入库安全规范"));
        String docCategory = String.valueOf(body.getOrDefault("docCategory", "STANDARD"));
        String standardCode = body.get("standardCode") != null ? String.valueOf(body.get("standardCode")) : null;
        String rawText = String.valueOf(body.getOrDefault("rawText", ""));
        String places = String.valueOf(body.getOrDefault("applicablePlaces", "production,storage,auxiliary"));

        Map<String, Object> aiReq = new HashMap<>();
        aiReq.put("doc_title", docTitle);
        aiReq.put("doc_category", docCategory);
        aiReq.put("standard_code", standardCode);
        aiReq.put("raw_text", rawText);
        aiReq.put("applicable_places", places);

        JSONObject fb = new JSONObject();
        fb.put("degraded", true);
        JSONObject res = aiClient.postJsonWithFallback("/api/v1/rag/ingest", aiReq, fb);
        if (res.getBooleanValue("degraded"))
        {
            EhsKbDocument doc = new EhsKbDocument();
            doc.setDocTitle(docTitle);
            doc.setDocCategory(docCategory);
            doc.setStandardCode(standardCode);
            doc.setChunkCount(1);
            doc.setCreateBy(resolveOperator());
            knowledgeMapper.insertDocFallback(doc);

            EhsKbChunk ch = new EhsKbChunk();
            ch.setDocId(doc.getDocId());
            ch.setChunkIndex(1);
            ch.setClauseNo("全文摘录");
            ch.setChunkText(rawText);
            ch.setApplicablePlaces(places);
            knowledgeMapper.insertChunkFallback(ch);

            res.put("doc_id", doc.getDocId());
            res.put("chunk_count", 1);
        }
        return success(res);
    }

    @PostMapping("/kb/upload")
    public AjaxResult uploadAndIngestDoc(
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "docTitle", required = false) String docTitle,
            @RequestParam(value = "docCategory", defaultValue = "STANDARD") String docCategory,
            @RequestParam(value = "standardCode", required = false) String standardCode,
            @RequestParam(value = "applicablePlaces", defaultValue = "production,storage,auxiliary") String applicablePlaces) throws Exception
    {
        String relUrl = FileUploadUtils.upload(GliHubConfig.getUploadPath(), file);
        String subPath = relUrl.replaceFirst("^" + Constants.RESOURCE_PREFIX, "");
        File localFile = new File(GliHubConfig.getProfile(), subPath).getAbsoluteFile();
        String title = (docTitle != null && !docTitle.isEmpty()) ? docTitle : file.getOriginalFilename();

        Map<String, Object> aiReq = new HashMap<>();
        aiReq.put("doc_title", title);
        aiReq.put("doc_category", docCategory);
        aiReq.put("standard_code", standardCode);
        aiReq.put("file_path", localFile.getAbsolutePath());
        aiReq.put("applicable_places", applicablePlaces);

        JSONObject fb = new JSONObject();
        fb.put("degraded", true);
        JSONObject res = aiClient.postJsonWithFallback("/api/v1/rag/ingest", aiReq, fb);
        if (res.getBooleanValue("degraded"))
        {
            EhsKbDocument doc = new EhsKbDocument();
            doc.setDocTitle(title);
            doc.setDocCategory(docCategory);
            doc.setStandardCode(standardCode);
            doc.setFilePath(relUrl);
            doc.setChunkCount(0);
            doc.setCreateBy(resolveOperator());
            knowledgeMapper.insertDocFallback(doc);
            res.put("doc_id", doc.getDocId());
        }
        return success(res);
    }

    @DeleteMapping("/kb/docs/{docId}")
    public AjaxResult deleteDoc(@PathVariable Long docId)
    {
        return toAjax(knowledgeMapper.deleteDocById(docId));
    }

    @GetMapping("/kb/recommend")
    public AjaxResult recommendLaws(
            @RequestParam("query") String query,
            @RequestParam(value = "placeType", required = false) String placeType,
            @RequestParam(value = "topK", defaultValue = "4") Integer topK)
    {
        Map<String, Object> aiReq = new HashMap<>();
        aiReq.put("query", query);
        aiReq.put("place_type", placeType);
        aiReq.put("top_k", topK);

        JSONObject fb = new JSONObject();
        fb.put("degraded", true);
        JSONObject res = aiClient.postJsonWithFallback("/api/v1/rag/search", aiReq, fb);
        if (res.getBooleanValue("degraded"))
        {
            List<EhsKbChunk> fallbackList = knowledgeMapper.searchChunksFallback(query, placeType, topK);
            return success(fallbackList);
        }
        return success(res.getJSONArray("items"));
    }

    @PostMapping(value = "/kb/chat/stream", produces = MediaType.TEXT_EVENT_STREAM_VALUE)
    public SseEmitter streamComplianceChat(@RequestBody Map<String, Object> body)
    {
        SseEmitter emitter = new SseEmitter(60000L);
        CompletableFuture.runAsync(() -> {
            try
            {
                aiClient.streamSsePost("/api/v1/rag/chat/stream", body, dataLine -> {
                    try
                    {
                        emitter.send(SseEmitter.event().data(dataLine));
                    }
                    catch (Exception ignored) {}
                }, () -> {
                    try
                    {
                        List<EhsKbChunk> rows = knowledgeMapper.searchChunksFallback("", null, 3);
                        Map<String, Object> delta = Map.of(
                                "type", "delta",
                                "delta", "【本地离线合规库】当前 AI 引擎离线，已从 PostgreSQL 知识库检索出 "
                                        + rows.size() + " 条安全生产标准条款供参考。");
                        emitter.send(SseEmitter.event().data(JSON.toJSONString(delta)));
                        emitter.send(SseEmitter.event().data("[DONE]"));
                    }
                    catch (Exception ignored) {}
                });
                emitter.complete();
            }
            catch (Exception ex)
            {
                emitter.completeWithError(ex);
            }
        });
        return emitter;
    }

    private String resolveOperator()
    {
        try { return getUsername(); } catch (Exception e) { return "admin"; }
    }
}
