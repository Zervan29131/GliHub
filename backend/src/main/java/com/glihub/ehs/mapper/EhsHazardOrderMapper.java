package com.glihub.ehs.mapper;

import java.util.List;
import java.util.Map;
import org.apache.ibatis.annotations.Param;
import com.glihub.ehs.domain.EhsHazardOrder;

/**
 * 隐患排查治理闭环工单 Mapper
 */
public interface EhsHazardOrderMapper
{
    List<EhsHazardOrder> selectOrderList(EhsHazardOrder query);

    EhsHazardOrder selectOrderById(@Param("orderId") Long orderId);

    int insertOrder(EhsHazardOrder order);

    int updateOrder(EhsHazardOrder order);

    int deleteOrderByIds(Long[] orderIds);

    int countOpenOrdersByDept(@Param("deptId") Long deptId);

    List<Map<String, Object>> selectOrderStatsByStatus();
}
