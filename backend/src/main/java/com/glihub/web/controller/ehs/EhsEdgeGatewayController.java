package com.glihub.web.controller.ehs;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.util.Map;
import jakarta.servlet.http.HttpServletRequest;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.*;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.core.controller.BaseController;
import com.glihub.common.core.domain.AjaxResult;
import com.glihub.ehs.service.EhsEdgeService;

@RestController
@RequestMapping("/ehs/edge")
public class EhsEdgeGatewayController extends BaseController
{
    @Autowired
    private EhsEdgeService edgeService;

    @PostMapping("/register")
    public AjaxResult registerNode(
            @RequestHeader(value = "X-Edge-Token", required = false) String token,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request)
    {
        if (!edgeService.verifyEdgeToken(token))
        {
            return AjaxResult.error(HttpStatus.UNAUTHORIZED.value(), "Invalid X-Edge-Token");
        }
        return success(edgeService.registerEdgeNode(body, request.getRemoteAddr()));
    }

    @PostMapping("/heartbeat")
    public AjaxResult heartbeat(
            @RequestHeader(value = "X-Edge-Token", required = false) String token,
            @RequestBody Map<String, Object> body,
            HttpServletRequest request)
    {
        if (!edgeService.verifyEdgeToken(token))
        {
            return AjaxResult.error(HttpStatus.UNAUTHORIZED.value(), "Invalid X-Edge-Token");
        }
        String base = request.getScheme() + "://" + request.getServerName() + ":" + request.getServerPort();
        return success(edgeService.handleHeartbeat(body, base));
    }

    @GetMapping("/config/{nodeCode}")
    public AjaxResult getNodeConfig(
            @RequestHeader(value = "X-Edge-Token", required = false) String token,
            @PathVariable String nodeCode)
    {
        if (!edgeService.verifyEdgeToken(token))
        {
            return AjaxResult.error(HttpStatus.UNAUTHORIZED.value(), "Invalid X-Edge-Token");
        }
        return success(edgeService.fetchNodeRemoteConfig(nodeCode));
    }

    @PostMapping("/alerts/batch")
    public AjaxResult receiveEdgeAlertsBatch(
            @RequestHeader(value = "X-Edge-Token", required = false) String token,
            @RequestBody Map<String, Object> body)
    {
        if (!edgeService.verifyEdgeToken(token))
        {
            return AjaxResult.error(HttpStatus.UNAUTHORIZED.value(), "Invalid X-Edge-Token");
        }
        return success(edgeService.ingestEdgeAlertsBatch(body));
    }

    @GetMapping("/ota/download/{modelFile:.+}")
    public ResponseEntity<Resource> downloadOtaModel(
            @RequestHeader(value = "X-Edge-Token", required = false) String token,
            @PathVariable String modelFile)
    {
        if (!edgeService.verifyEdgeToken(token))
        {
            return ResponseEntity.status(HttpStatus.UNAUTHORIZED).build();
        }
        String safeName = Paths.get(modelFile).getFileName().toString();
        Path file = Paths.get(GliHubConfig.getModelsDir(), safeName).toAbsolutePath();
        if (!Files.exists(file))
        {
            return ResponseEntity.notFound().build();
        }
        Resource res = new FileSystemResource(file.toFile());
        return ResponseEntity.ok()
                .contentType(MediaType.APPLICATION_OCTET_STREAM)
                .header(HttpHeaders.CONTENT_DISPOSITION, "attachment; filename=\"" + safeName + "\"")
                .body(res);
    }

    // ==================== Web Console Management Endpoints ====================

    @GetMapping("/nodes")
    public AjaxResult listNodes()
    {
        return success(edgeService.listEdgeNodesWithDetails());
    }

    @PutMapping("/channels/roi")
    public AjaxResult updateChannelRoi(@RequestBody Map<String, Object> body)
    {
        return success(edgeService.updateChannelRoi(body));
    }

    @GetMapping("/ota/models")
    public AjaxResult listOtaModels()
    {
        return success(edgeService.listAvailableOtaModels());
    }

    @PostMapping("/ota/push")
    public AjaxResult pushOtaModel(@RequestBody Map<String, Object> body)
    {
        String nodeCode = String.valueOf(body.getOrDefault("nodeCode", "edge-chem-zone-01"));
        String modelFile = String.valueOf(body.getOrDefault("targetModelFile", "yolo26n.int8.onnx"));
        String op = "admin";
        try { op = getUsername(); } catch (Exception ignored) {}
        return success(edgeService.createOtaTask(nodeCode, modelFile, op));
    }
}
