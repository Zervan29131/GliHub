import base64
import json
from pathlib import Path
from typing import List, Optional
import httpx
from pydantic import BaseModel

from adapters.base import DetectionBox
from config import settings


class VlmReviewResult(BaseModel):
    reviewed: bool = True
    vlm_model: str
    is_real_hazard: bool
    violation_type: str
    severity: str  # CRITICAL / HIGH / MEDIUM / LOW
    description: str
    suggestion: str
    fallback_rule_used: bool = False


PLACE_CN = {
    "production": "生产场所",
    "storage": "储存场所",
    "auxiliary": "公辅场所",
}


class VlmReviewer:
    """
    通过 OpenAI-Compatible API (/v1/chat/completions) 对接 Qwen3-VL / Qwen2.5-VL / InternVL3。
    当本地 Ollama 或远端 VLM 端点未启动/未配置密钥时，自动启用工业 EHS 规则复核引擎兜底。
    """

    async def is_endpoint_reachable(self) -> bool:
        if not settings.vlm_base_url:
            return False
        if "localhost:11434" not in settings.vlm_base_url and not settings.vlm_api_key:
            return False
        try:
            headers = {}
            if settings.vlm_api_key:
                headers["Authorization"] = f"Bearer {settings.vlm_api_key}"
            async with httpx.AsyncClient(timeout=2.0) as client:
                resp = await client.get(f"{settings.vlm_base_url.rstrip('/')}/models", headers=headers)
                return resp.status_code == 200
        except Exception:
            return False

    async def review(
        self,
        image_path: Path,
        detections: List[DetectionBox],
        place_type: str = "production",
        area_name: str = "现场作业区",
        hazard_context: Optional[str] = None,
        prompt_text: Optional[str] = None,
    ) -> VlmReviewResult:
        if await self.is_endpoint_reachable():
            try:
                return await self._call_openai_compatible_vlm(
                    image_path=image_path,
                    detections=detections,
                    place_type=place_type,
                    area_name=area_name,
                    hazard_context=hazard_context,
                    prompt_text=prompt_text,
                )
            except Exception:
                pass

        return self._rule_based_review(
            detections=detections,
            place_type=place_type,
            area_name=area_name,
            hazard_context=hazard_context,
            prompt_text=prompt_text,
        )

    async def _call_openai_compatible_vlm(
        self,
        image_path: Path,
        detections: List[DetectionBox],
        place_type: str,
        area_name: str,
        hazard_context: Optional[str],
        prompt_text: Optional[str],
    ) -> VlmReviewResult:
        img_b64 = base64.b64encode(image_path.read_bytes()).decode("utf-8")
        det_summary = [
            {"label": d.label_zh, "conf": d.confidence, "bbox": d.bbox_xyxy, "violation": d.is_violation}
            for d in detections
        ]
        place_label = PLACE_CN.get(place_type, "工业作业区")
        sys_prompt = (
            "你是一名资深工业安全生产(EHS)视觉复核专家。请结合第一阶段目标检测候选框与图像内容进行二次复核，"
            "排除光影或安全帽遮挡造成的误报，并严格输出 JSON 对象，包含字段："
            "is_real_hazard (bool), violation_type (str), severity (CRITICAL|HIGH|MEDIUM|LOW), "
            "description (str), suggestion (str)。"
        )
        user_text = (
            f"场所类别：{place_label}；作业区域：{area_name}；"
            f"关联危险源背景：{hazard_context or '常规工业生产巡检'}；"
            f"专项排查词：{prompt_text or '无'}；"
            f"第一阶段检测框结果：{json.dumps(det_summary, ensure_ascii=False)}。"
            "请判断是否存在真实安全隐患并给出专业整改建议。"
        )
        headers = {"Content-Type": "application/json"}
        if settings.vlm_api_key:
            headers["Authorization"] = f"Bearer {settings.vlm_api_key}"

        payload = {
            "model": settings.vlm_model,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": sys_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": user_text},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                    ],
                },
            ],
        }
        async with httpx.AsyncClient(timeout=settings.vlm_timeout_sec) as client:
            resp = await client.post(
                f"{settings.vlm_base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            )
            resp.raise_for_status()
            content = resp.json()["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return VlmReviewResult(
                reviewed=True,
                vlm_model=settings.vlm_model,
                is_real_hazard=bool(parsed.get("is_real_hazard", True)),
                violation_type=str(parsed.get("violation_type", "现场安全违章")),
                severity=str(parsed.get("severity", "HIGH")).upper(),
                description=str(parsed.get("description", "")),
                suggestion=str(parsed.get("suggestion", "")),
                fallback_rule_used=False,
            )

    def _rule_based_review(
        self,
        detections: List[DetectionBox],
        place_type: str,
        area_name: str,
        hazard_context: Optional[str],
        prompt_text: Optional[str],
    ) -> VlmReviewResult:
        place_label = PLACE_CN.get(place_type, "作业场所")
        violations = [d for d in detections if d.is_violation]
        helmets = [d for d in detections if d.label in ("With Helmet", "helmet")]

        if not violations:
            if helmets:
                return VlmReviewResult(
                    reviewed=True,
                    vlm_model="ehs-rule-reviewer-v2 (VLM离线兜底)",
                    is_real_hazard=False,
                    violation_type="个体防护穿戴合规",
                    severity="LOW",
                    description=(
                        f"【{place_label}·{area_name}】检出 {len(helmets)} 名作业人员均已规范佩戴安全帽"
                        f"（平均置信度 {sum(h.confidence for h in helmets)/len(helmets):.2f}），未发现防护缺失或违章行为。"
                    ),
                    suggestion="保持现有个体防护管理措施，继续按班次执行常规巡检。",
                    fallback_rule_used=True,
                )
            return VlmReviewResult(
                reviewed=True,
                vlm_model="ehs-rule-reviewer-v2 (VLM离线兜底)",
                is_real_hazard=False,
                violation_type="未检出异常目标",
                severity="LOW",
                description=f"【{place_label}·{area_name}】当前监控画面检出 {len(detections)} 个常规目标，未发现明显违章与险情特征。",
                suggestion="建议维持重点设备与通道定时抓拍监测。",
                fallback_rule_used=True,
            )

        no_helmet_cnt = sum(1 for v in violations if v.label in ("without_helmet", "no_helmet"))
        phone_cnt = sum(1 for v in violations if v.label == "cell phone")
        fire_smoke_cnt = sum(1 for v in violations if v.label in ("fire", "smoke"))

        if fire_smoke_cnt > 0:
            v_type = "疑似烟火/泄漏初期险情"
            sev = "CRITICAL"
            desc = f"【{place_label}·{area_name}】检出 {fire_smoke_cnt} 处疑似烟火异常目标，结合区域危险源（{hazard_context or '易燃易爆装置'}），判定为最高等级警情。"
            sugg = "立即启动现场专项应急处置行动卡，联锁关闭上下游紧急切断阀，组织人员向上风向疏散并核实现场火情。"
        elif no_helmet_cnt > 0:
            v_type = "未规范佩戴安全帽违章"
            sev = "HIGH" if place_type in ("production", "storage") else "MEDIUM"
            desc = (
                f"【{place_label}·{area_name}】复核确认存在 {no_helmet_cnt} 名作业人员头肩区域未佩戴安全帽"
                f"（同画面合规佩戴 {len(helmets)} 人），违反进入生产/储存作业区个体防护强制规定。"
            )
            sugg = "立即通过现场广播提醒违章人员停止作业，责令当班安全员督促补戴符合 GB 2811 标准安全帽，并上传复查照片销项。"
        elif phone_cnt > 0:
            v_type = "高危防爆区违规使用非防爆手机"
            sev = "HIGH"
            desc = f"【{place_label}·{area_name}】检出 {phone_cnt} 处违规使用手机行为，在易燃易爆场所存在射频与电火花引燃风险。"
            sugg = "立即制止非防爆通讯设备使用，核查入场静电消除与电子设备寄存登记台账。"
        else:
            top_v = violations[0]
            v_type = f"专项排查违章（{top_v.label_zh}）"
            sev = "MEDIUM"
            desc = f"【{place_label}·{area_name}】依据排查要求（{prompt_text or top_v.label_zh}）检出 {len(violations)} 处异常目标（最高置信度 {top_v.confidence:.2f}）。"
            sugg = "安排属地责任人前往现场核实清理，消除通道占压或物品违规摆放隐患后拍照闭环。"

        return VlmReviewResult(
            reviewed=True,
            vlm_model="ehs-rule-reviewer-v2 (VLM离线兜底)",
            is_real_hazard=True,
            violation_type=v_type,
            severity=sev,
            description=desc,
            suggestion=sugg,
            fallback_rule_used=True,
        )


vlm_reviewer = VlmReviewer()
