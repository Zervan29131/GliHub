from datetime import datetime
import json
from typing import Any, Dict, List, Optional
import httpx

from config import settings
from rag.retriever import rag_engine

PLACE_CN = {
    "production": "生产场所",
    "storage": "储存场所",
    "auxiliary": "公辅场所",
}


async def _try_llm_json_or_text(sys_prompt: str, user_prompt: str, as_json: bool = False) -> Optional[Any]:
    llm_ready = bool(settings.llm_base_url) and (
        "localhost:11434" in settings.llm_base_url or bool(settings.llm_api_key)
    )
    if not llm_ready:
        return None
    headers = {"Content-Type": "application/json"}
    if settings.llm_api_key:
        headers["Authorization"] = f"Bearer {settings.llm_api_key}"
    payload: Dict[str, Any] = {
        "model": settings.llm_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": sys_prompt},
            {"role": "user", "content": user_prompt},
        ],
    }
    if as_json:
        payload["response_format"] = {"type": "json_object"}
    try:
        async with httpx.AsyncClient(timeout=settings.llm_timeout_sec) as client:
            resp = await client.post(
                f"{settings.llm_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload
            )
            if resp.status_code != 200:
                return None
            txt = resp.json()["choices"][0]["message"]["content"]
            return json.loads(txt) if as_json else txt
    except Exception:
        return None


async def recommend_eval_params(
    eval_method: str,
    place_type: str,
    area_name: str,
    hazard_profile: Optional[Dict] = None,
    recent_alerts_count: int = 0,
    open_orders_count: int = 0,
) -> Dict:
    """
    基于危险源理化档案与近期视觉违章/未闭环隐患工单数，辅助推荐 Dow F&EI 或 LEC 评价参数（强制要求人工确认）。
    """
    method = eval_method.upper()
    hz = hazard_profile or {}
    chem = hz.get("chemical_name") or ("甲醇" if place_type == "storage" else "一氧化碳")
    mf = float(hz.get("dow_mf") or (16.0 if "甲醇" in chem else 14.0 if "一氧化碳" in chem else 21.0))

    rationale: List[str] = []
    if method == "DOW":
        f1 = 2.2 if place_type == "production" else 1.8 if place_type == "storage" else 1.4
        f2 = 2.1 if hz.get("major_hazard_grade", "非") != "非重大危险源" else 1.5
        if open_orders_count > 0 or recent_alerts_count > 0:
            c_factor = round(min(0.95, 0.72 + 0.05 * (open_orders_count + recent_alerts_count)), 2)
            rationale.append(
                f"当前作业区存在 {recent_alerts_count} 条近期视觉告警、{open_orders_count} 项未闭环隐患，安全措施补偿系数 C 由基准 0.72 保守上调至 {c_factor}。"
            )
        else:
            c_factor = 0.72
            rationale.append("近期无未闭环隐患，SIS 联锁与气体报警完好，安全补偿系数 C 推荐取 0.72。")
        rationale.insert(0, f"依据《道氏火灾爆炸指数评价导则》，介质「{chem}」物质系数 MF 标准取值为 {mf}。")
        rec_params = {"mf": mf, "f1": f1, "f2": f2, "cFactor": c_factor}
    else:
        # LEC 动态风险联动核心逻辑
        base_l = 3.0
        if open_orders_count >= 2 or recent_alerts_count >= 2:
            base_l = 6.0
            rationale.append(
                f"【动态风险上调预警】该区域累计 {recent_alerts_count} 次视觉违章告警及 {open_orders_count} 张未闭环隐患工单，事故可能性 L 建议由 3（可能但不经常）上调至 6（相当可能）！"
            )
        else:
            rationale.append("基于常规巡检频次与历史隐患记录，事故发生可能性 L 推荐取 3（可能，但不经常）。")
        e_val = 6.0 if place_type in ("production", "storage") else 3.0
        c_val = 15.0 if hz.get("risk_level") == "重大风险" else 7.0
        rationale.append(f"该单元属于{PLACE_CN.get(place_type, '生产场所')}，当班暴露频繁程度 E 取 {e_val}，潜在后果严重度 C 取 {c_val}。")
        rec_params = {"l": base_l, "e": e_val, "c": c_val}

    return {
        "eval_method": method,
        "recommended_params": rec_params,
        "rationale_items": rationale,
        "requires_human_confirm": True,
        "dynamic_re_eval_triggered": (open_orders_count + recent_alerts_count) >= 2,
    }


async def generate_eval_report(
    place_type: str,
    area_name: str,
    eval_summary: Dict[str, Any],
    hazard_profiles: Optional[List[Dict]] = None,
    alert_stats: Optional[Dict] = None,
    order_stats: Optional[Dict] = None,
) -> Dict:
    place_label = PLACE_CN.get(place_type, "工业作业场所")
    laws = await rag_engine.search(f"{place_label} 安全评价 重大危险源 隐患治理", place_type=place_type, top_k=4)

    sys_prompt = (
        "你是一名国家注册安全工程师。请基于下方精确的确定性数学公式计算结果（严禁改动任何数值）、"
        "现场 AI 视觉监测统计与法规依据，撰写一份结构严谨的 Markdown 格式《安全评价与动态风险研判报告》。"
    )
    user_prompt = json.dumps(
        {
            "place_label": place_label,
            "area_name": area_name,
            "deterministic_results": eval_summary,
            "hazards": hazard_profiles or [],
            "vision_alerts": alert_stats or {},
            "hazard_orders": order_stats or {},
            "cited_laws": laws,
        },
        ensure_ascii=False,
    )
    llm_md = await _try_llm_json_or_text(sys_prompt, user_prompt, as_json=False)
    if llm_md:
        return {
            "report_markdown": llm_md,
            "generated_by": settings.llm_model,
            "cited_laws": laws,
        }

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    dow = eval_summary.get("dow") or {}
    lec = eval_summary.get("lec") or {}
    tnt = eval_summary.get("tnt") or {}
    scl = eval_summary.get("scl") or {}
    a_total = (alert_stats or {}).get("total", 0)
    o_open = (order_stats or {}).get("open", 0)

    law_bullets = "\n".join(
        [f"- **{c['doc_title']} {c['clause_no']}**：{c['chunk_text']}" for c in laws]
    )

    md = f"""# GliHub 安全评价与动态风险研判报告

- **评价单元**：{place_label} — {area_name}
- **生成时间**：{now_str}
- **计算准则**：物理与数学确定性公式精确求解 + 视觉隐患闭环联动分析

---

## 一、四大安全评价确定性计算结论

1. **道氏火灾、爆炸危险指数法（Dow F&EI）**
   - 工艺单元：{dow.get('unitName', area_name)}
   - 单元危险系数 $F_3$：**{dow.get('f3', '-')}**；初始火灾爆炸指数 $F\\&EI$：**{dow.get('fei', '-')}**（{dow.get('level', '-')}）
   - 安全措施补偿后 $F\\&EI'$：**{dow.get('compensatedFei', '-')}**（{dow.get('compLevel', '-')}），暴露区域半径 **{dow.get('radius', '-')} m**（面积 **{dow.get('area', '-')} m²**）。
2. **作业条件危险性分析法（LEC）**
   - 评价作业活动：{lec.get('jobName', '常规巡检与特种作业')}
   - 危险性分值 $D = L \\times E \\times C$：**{lec.get('d', '-')}**，风险等级判定：**{lec.get('grade', '-')}（{lec.get('levelText', '-')}）**。
3. **重大危险源事故后果模拟法（TNT 当量法）**
   - 折算 TNT 当量 $W_{{TNT}}$：**{tnt.get('wtnt', '-')} kg**
   - 冲击波伤害圈：死亡半径 $R_1 =$ **{tnt.get('r1', '-')} m**、重伤半径 $R_2 =$ **{tnt.get('r2', '-')} m**、轻伤半径 $R_3 =$ **{tnt.get('r3', '-')} m**、财产损失半径 $R_4 =$ **{tnt.get('r4', '-')} m**。
4. **安全检查表法（SCL）合规度**
   - 共核查 **{scl.get('total', 0)}** 项，符合 **{scl.get('pass', 0)}** 项，不符合 **{scl.get('fail', 0)}** 项，综合合规率 **{scl.get('rate', 100)}%**。

---

## 二、AI 视觉感知与隐患治理动态联动评估

- 近期智能视觉监控累计捕获告警 **{a_total}** 起，当前待闭环整改工单 **{o_open}** 项。
- **动态风险研判意见**：{"当前存在未闭环隐患工单，建议立即督办销项并在整改完成后复核 LEC 风险值。" if o_open > 0 else "当前隐患工单闭环情况良好，现场联锁及个体防护处于受控状态。"}

---

## 三、法规与国家技术标准合规引用

{law_bullets}

---

## 四、综合风险管控与整改对策建议

1. **工程技术措施**：严格校验可燃/有毒气体检测报警器（GB/T 50493）与 SIS 紧急切断联锁阀完好性，确保 TNT 重伤半径（{tnt.get('r2', '-')} m）内严禁非防爆作业及无关人员滞留。
2. **个体防护与行为监管**：依托 GliHub 视觉双阶段复核中心持续监测未佩戴安全帽、违规动火与通道占压行为，严格执行「告警—派单—复查照片 AI 核验」闭环。
"""
    return {
        "report_markdown": md,
        "generated_by": "glihub-deterministic-report-engine-v2",
        "cited_laws": laws,
    }
