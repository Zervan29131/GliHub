from datetime import datetime
import json
from typing import Any, Dict, List
from agents.eval_agent import _try_llm_json_or_text
from config import settings


async def generate_emergency_action_card(
    hazard_profile: Dict[str, Any],
    accident_type: str,
    leak_mass_kg: float,
    wind_direction: str,
    wind_speed_ms: float,
    tnt_result: Dict[str, Any],
    affected_equips: List[Dict[str, Any]],
    affected_staff_count: int,
) -> Dict[str, Any]:
    """
    结合危险源理化特性、TNT 当量冲击波半径、风向与波及范围内特种设备/在岗人数，秒级生成《现场应急处置行动卡》。
    """
    hz_name = hazard_profile.get("hazard_name", "重点危险源单元")
    chem = hazard_profile.get("chemical_name", "易燃易爆危化品")
    ppe_raw = hazard_profile.get("ppe_requirements") or "正压式空气呼吸器（SCBA）、重型防化服、防爆对讲机"
    ppe_list = [p.strip() for p in ppe_raw.replace("、", ",").replace("；", ",").split(",") if p.strip()]

    r1 = tnt_result.get("r1", 15)
    r2 = tnt_result.get("r2", 35)
    r3 = tnt_result.get("r3", 65)
    evac_perimeter = int(float(r3) * 1.2) + 10
    upwind_map = {
        "东南风": "西北方向（上风向）或东北侧风向高地",
        "东风": "正西方向（上风向）应急集合点",
        "南风": "正北方向（上风向）安全集结点",
        "西北风": "东南方向（上风向）主大门集结点",
        "北风": "正南方向（上风向）安全集结点",
    }
    evac_route = upwind_map.get(wind_direction, f"逆「{wind_direction}」上风向及侧上风向紧急疏散通道")

    equip_names = [e.get("postName") or e.get("equip_name") or str(e) for e in affected_equips]
    equip_str = "、".join(equip_names) if equip_names else "周边毗邻工艺管线与配电设施"

    immediate_steps = [
        f"【0~1 min 紧急切断】立即触发「{hz_name}」SIS/ESD 紧急切断阀，封锁上下游物料进出，严禁使用非防爆工具。",
        f"【1~3 min 警戒疏散】以泄漏爆炸中心划定 {evac_perimeter}m 警戒圈（覆盖轻伤半径 R3={r3}m），引导波及范围内 {affected_staff_count} 名在岗人员沿{evac_route}撤离。",
        f"【3~5 min 工程控险】开启固定式水幕/抗溶性泡沫喷淋系统对毗邻重点设备（{equip_str}）持续冷却稀释，切断警戒区内非防爆电源。",
        "【持续监测】抢险组佩戴正压式空气呼吸器在边界下风向每 5 分钟测定可燃与有毒气体浓度，严防二次回燃爆炸。",
    ]

    report_checklist = [
        "向厂区应急总指挥与中控室（DCS）报告事故发生时间、介质名称（" + chem + "）及泄漏预估量（" + str(leak_mass_kg) + " kg）",
        f"核对当班考勤与人员定位，清点波及区 {affected_staff_count} 名作业人员撤离到位情况",
        "若火势/泄漏不可控，立即拨打 119、120 并在 1 小时内向属地应急管理局上报",
    ]

    sys_prompt = "你是危化品企业应急救援总指挥助手，请根据推演参数输出简洁、可直接下发班组执行的 Markdown 格式《现场应急处置行动卡》。"
    llm_md = await _try_llm_json_or_text(
        sys_prompt,
        json.dumps(
            {
                "hazard": hazard_profile,
                "accident_type": accident_type,
                "leak_mass_kg": leak_mass_kg,
                "wind": f"{wind_direction} {wind_speed_ms}m/s",
                "tnt_radii": tnt_result,
                "affected_equips": equip_names,
                "affected_staff_count": affected_staff_count,
                "evac_route": evac_route,
            },
            ensure_ascii=False,
        ),
        as_json=False,
    )

    if not llm_md:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        steps_md = "\n".join([f"{i+1}. {s}" for i, s in enumerate(immediate_steps)])
        ppe_md = " | ".join([f"`{p}`" for p in ppe_list])
        rep_md = "\n".join([f"- [ ] {r}" for r in report_checklist])
        llm_md = f"""# 现场应急处置行动卡（AI 秒级推演）

> **触发单元**：{hz_name}（介质：{chem}） | **事故情景**：{accident_type} | **生成时间**：{now_str}

## 一、爆炸冲击波与波及范围研判
- **模拟泄漏质量**：`{leak_mass_kg} kg`（折算 TNT 当量：`{tnt_result.get('wtnt', '-')} kg`）
- **气象条件**：{wind_direction}（风速 `{wind_speed_ms} m/s`）
- **核心伤害圈**：死亡半径 $R_1 = {r1}\\text{{ m}}$ | 重伤半径 $R_2 = {r2}\\text{{ m}}$ | 轻伤半径 $R_3 = {r3}\\text{{ m}}$ | 财产损失半径 $R_4 = {tnt_result.get('r4', '-')}\\text{{ m}}$
- **受波及对象**：预计波及在岗人员 **{affected_staff_count} 人**；波及关键设备：**{equip_str}**

## 二、初期应急处置四步指令
{steps_md}

## 三、强制个体防护装备（PPE）清单
{ppe_md}

## 四、最优疏散路线建议
- **推荐撤离方向**：**{evac_route}**，严禁顺风向或沿低洼管沟撤离，紧急警戒半径不小于 **{evac_perimeter} m**。

## 五、应急信息上报核查单
{rep_md}
"""

    return {
        "action_card_markdown": llm_md,
        "immediate_steps": immediate_steps,
        "ppe_list": ppe_list,
        "evacuation_route": evac_route,
        "evacuation_perimeter_m": evac_perimeter,
        "report_checklist": report_checklist,
        "generated_by": settings.llm_model if settings.llm_api_key else "glihub-emergency-tactical-engine-v2",
    }
