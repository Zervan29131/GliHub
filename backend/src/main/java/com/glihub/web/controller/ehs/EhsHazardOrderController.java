package com.glihub.web.controller.ehs;

import java.io.File;
import java.util.List;
import java.util.Map;
import java.util.concurrent.ThreadLocalRandom;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;
import com.glihub.common.config.GliHubConfig;
import com.glihub.common.constant.Constants;
import com.glihub.common.core.controller.BaseController;
import com.glihub.common.core.domain.AjaxResult;
import com.glihub.common.core.page.TableDataInfo;
import com.glihub.common.utils.file.FileUploadUtils;
import com.glihub.ehs.domain.EhsHazardOrder;
import com.glihub.ehs.mapper.EhsHazardOrderMapper;
import com.glihub.ehs.service.EhsClosedLoopService;

@RestController
@RequestMapping("/ehs/order")
public class EhsHazardOrderController extends BaseController
{
    @Autowired
    private EhsHazardOrderMapper orderMapper;
    @Autowired
    private EhsClosedLoopService closedLoopService;

    @GetMapping("/list")
    public TableDataInfo list(EhsHazardOrder query)
    {
        startPage();
        List<EhsHazardOrder> rows = orderMapper.selectOrderList(query);
        return getDataTable(rows);
    }

    @GetMapping("/{orderId}")
    public AjaxResult detail(@PathVariable Long orderId)
    {
        return success(orderMapper.selectOrderById(orderId));
    }

    @PostMapping
    public AjaxResult create(@RequestBody EhsHazardOrder order)
    {
        if (order.getOrderNo() == null || order.getOrderNo().isEmpty())
        {
            order.setOrderNo("HD-" + System.currentTimeMillis() + "-" + ThreadLocalRandom.current().nextInt(10, 99));
        }
        order.setCreateBy(safeUser());
        orderMapper.insertOrder(order);
        return success(order);
    }

    @PutMapping
    public AjaxResult modify(@RequestBody EhsHazardOrder order)
    {
        order.setUpdateBy(safeUser());
        return toAjax(orderMapper.updateOrder(order));
    }

    @DeleteMapping("/{orderIds}")
    public AjaxResult remove(@PathVariable Long[] orderIds)
    {
        return toAjax(orderMapper.deleteOrderByIds(orderIds));
    }

    @PostMapping("/{orderId}/rectify-upload")
    public AjaxResult uploadRectifyAndRecheck(
            @PathVariable Long orderId,
            @RequestParam("file") MultipartFile file,
            @RequestParam(value = "rectifyNote", required = false) String rectifyNote) throws Exception
    {
        String relUrl = FileUploadUtils.upload(GliHubConfig.getUploadPath(), file);
        String subPath = relUrl.replaceFirst("^" + Constants.RESOURCE_PREFIX, "");
        File localFile = new File(GliHubConfig.getProfile(), subPath).getAbsoluteFile();

        Map<String, Object> res = closedLoopService.submitOrderRectification(
                orderId, localFile.getAbsolutePath(), relUrl, rectifyNote, safeUser());
        return success(res);
    }

    @PostMapping("/{orderId}/rectify-sample")
    public AjaxResult rectifyWithSample(@PathVariable Long orderId, @RequestBody Map<String, Object> body)
    {
        String sampleRel = String.valueOf(body.getOrDefault("sampleRelPath", "archive/images/BikesHelmets0.png"));
        if (sampleRel.contains(".."))
        {
            return error("非法路径");
        }
        File sampleFile = new File(GliHubConfig.getSampleImageDir(), sampleRel).getAbsoluteFile();
        String note = String.valueOf(body.getOrDefault("rectifyNote", "现场已完成安全帽补戴与违章整改复查"));
        Map<String, Object> res = closedLoopService.submitOrderRectification(
                orderId, sampleFile.getAbsolutePath(), "/sample-images/" + sampleRel, note, safeUser());
        return success(res);
    }

    private String safeUser()
    {
        try { return getUsername(); } catch (Exception e) { return "admin"; }
    }
}
