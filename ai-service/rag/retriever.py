from __future__ import annotations

import hashlib
import json
from typing import Any, AsyncGenerator, Dict, List, Optional
import httpx
import numpy as np

from config import settings
from rag.parser import extract_text_from_file, split_legal_clauses

BUILTIN_FALLBACK_CLAUSES: List[Dict[str, Any]] = [
    {
        "chunk_id": 9001,
        "doc_id": 1,
        "doc_title": "《中华人民共和国安全生产法》",
        "doc_category": "LAW",
        "standard_code": "主席令第八十八号",
        "clause_no": "第四十五条",
        "chunk_text": "生产经营单位必须为从业人员提供符合国家标准或者行业标准的劳动防护用品，并监督、教育从业人员按照使用规则佩戴、使用。",
        "score": 0.92,
    },
    {
        "chunk_id": 9002,
        "doc_id": 2,
        "doc_title": "《个体防护装备配备规范 第2部分：石油、化工、天然气》",
        "doc_category": "STANDARD",
        "standard_code": "GB 39800.2-2020",
        "clause_no": "5.1",
        "chunk_text": "进入石油化工生产装置区、储罐区及装卸栈台的所有作业与巡检人员，必须全程规范佩戴符合 GB 2811 标准的安全帽及防静电工作服。",
        "score": 0.90,
    },
    {
        "chunk_id": 9003,
        "doc_id": 3,
        "doc_title": "《危险化学品重大危险源辨识》",
        "doc_category": "STANDARD",
        "standard_code": "GB 18218-2018",
        "clause_no": "4.2",
        "chunk_text": "危险化学品重大危险源的辨识依据是危险化学品的危险特性及其数量；单元内存在多种危险物质时按 q1/Q1 + q2/Q2 + ... >= 1 判定。",
        "score": 0.88,
    },
]


def _connect_pg():
    try:
        import psycopg  # type: ignore

        return psycopg.connect(settings.pg_dsn), "psycopg3"
    except ImportError:
        import psycopg2  # type: ignore

        return psycopg2.connect(settings.pg_dsn), "psycopg2"


def compute_deterministic_embedding(text: str, dim: int = 1024) -> List[float]:
    vec = np.zeros(dim, dtype=np.float32)
    clean = text.strip().lower()
    if not clean:
        return vec.tolist()
    tokens = [clean[i : i + 2] for i in range(max(1, len(clean) - 1))] + list(clean)
    for tok in tokens:
        h = int(hashlib.md5(tok.encode("utf-8")).hexdigest()[:8], 16)
        idx = h % dim
        sign = 1.0 if ((h >> 8) & 1) == 0 else -1.0
        vec[idx] += sign
    norm = float(np.linalg.norm(vec))
    if norm > 1e-6:
        vec /= norm
    return [round(float(x), 5) for x in vec.tolist()]


class EhsRagEngine:
    def has_pgvector(self) -> bool:
        try:
            conn, _ = _connect_pg()
            with conn:
                with conn.cursor() as cur:
                    cur.execute("SELECT 1 FROM pg_extension WHERE extname = 'vector'")
                    return cur.fetchone() is not None
        except Exception:
            return False

    async def embed_text(self, text: str) -> List[float]:
        if settings.embedding_base_url:
            try:
                headers = {"Content-Type": "application/json"}
                if settings.embedding_api_key:
                    headers["Authorization"] = f"Bearer {settings.embedding_api_key}"
                async with httpx.AsyncClient(timeout=12.0) as client:
                    resp = await client.post(
                        f"{settings.embedding_base_url.rstrip('/')}/embeddings",
                        headers=headers,
                        json={"model": settings.embedding_model, "input": text},
                    )
                    resp.raise_for_status()
                    emb = resp.json()["data"][0]["embedding"]
                    if len(emb) == settings.embedding_dim:
                        return emb
            except Exception:
                pass
        return compute_deterministic_embedding(text, settings.embedding_dim)

    async def ingest_document(
        self,
        doc_title: str,
        doc_category: str = "STANDARD",
        standard_code: Optional[str] = None,
        file_path: Optional[str] = None,
        raw_text: Optional[str] = None,
        applicable_places: str = "production,storage,auxiliary",
        notice_id: Optional[int] = None,
    ) -> Dict[str, Any]:
        text_body = raw_text or ""
        ocr_used = "raw_text"
        if file_path:
            resolved = settings.resolve_path(file_path)
            if resolved and resolved.exists():
                text_body = extract_text_from_file(resolved)
                ocr_used = "pypdf_parser" if resolved.suffix.lower() == ".pdf" else "text_parser"

        clauses = split_legal_clauses(text_body, applicable_places=applicable_places)
        pgvec = self.has_pgvector()

        conn, _ = _connect_pg()
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO ehs_kb_document (notice_id, doc_title, doc_category, standard_code, file_path, ocr_engine, chunk_count, parse_status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'READY')
                    RETURNING doc_id
                    """,
                    (notice_id, doc_title, doc_category, standard_code, file_path, ocr_used, len(clauses)),
                )
                doc_id = cur.fetchone()[0]

                for idx, ch in enumerate(clauses, start=1):
                    emb = await self.embed_text(f"{doc_title} {ch['clause_no']} {ch['chunk_text']}")
                    emb_json = json.dumps(emb)
                    if pgvec:
                        vec_literal = "[" + ",".join(str(v) for v in emb) + "]"
                        cur.execute(
                            """
                            INSERT INTO ehs_kb_chunk (doc_id, chunk_index, clause_no, chunk_text, applicable_places, hazard_tags, embedding_json, embedding)
                            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb, %s::vector)
                            """,
                            (doc_id, idx, ch["clause_no"], ch["chunk_text"], ch["applicable_places"], ch["hazard_tags"], emb_json, vec_literal),
                        )
                    else:
                        cur.execute(
                            """
                            INSERT INTO ehs_kb_chunk (doc_id, chunk_index, clause_no, chunk_text, applicable_places, hazard_tags, embedding_json)
                            VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
                            """,
                            (doc_id, idx, ch["clause_no"], ch["chunk_text"], ch["applicable_places"], ch["hazard_tags"], emb_json),
                        )
            conn.commit()

        return {"doc_id": doc_id, "chunk_count": len(clauses), "pgvector_indexed": pgvec}

    async def search(
        self,
        query: str,
        place_type: Optional[str] = None,
        top_k: int = 4,
    ) -> List[Dict[str, Any]]:
        q_emb = np.array(await self.embed_text(query), dtype=np.float32)
        q_terms = [t for t in query.replace("，", " ").replace("、", " ").split() if t]
        domain_kws = [
            kw
            for kw in ["安全帽", "个体防护", "动火", "受限空间", "重大危险源", "储罐", "甲醇", "一氧化碳", "静电", "安全评价", "隐患", "防雷", "仓库"]
            if kw in query
        ]

        try:
            conn, _ = _connect_pg()
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        SELECT c.chunk_id, c.doc_id, c.clause_no, c.chunk_text, c.applicable_places, c.hazard_tags, c.embedding_json,
                               d.doc_title, d.doc_category, d.standard_code
                        FROM ehs_kb_chunk c
                        JOIN ehs_kb_document d ON c.doc_id = d.doc_id
                        ORDER BY c.chunk_id
                        """
                    )
                    cols = [desc[0] for desc in cur.description]
                    rows = [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception:
            return BUILTIN_FALLBACK_CLAUSES[: max(1, top_k)]

        if not rows:
            return BUILTIN_FALLBACK_CLAUSES[: max(1, top_k)]

        scored: List[Dict[str, Any]] = []
        for r in rows:
            if place_type and r["applicable_places"] and place_type not in r["applicable_places"]:
                place_bonus = -0.05
            else:
                place_bonus = 0.08 if place_type else 0.0

            full_txt = f"{r['doc_title']} {r['clause_no'] or ''} {r['chunk_text']} {r['hazard_tags'] or ''}"
            emb_raw = r["embedding_json"]
            if isinstance(emb_raw, str):
                emb_raw = json.loads(emb_raw)
            if emb_raw:
                c_vec = np.array(emb_raw, dtype=np.float32)
            else:
                c_vec = np.array(compute_deterministic_embedding(full_txt, len(q_emb)), dtype=np.float32)

            denom = (float(np.linalg.norm(q_emb)) * float(np.linalg.norm(c_vec))) or 1.0
            cos_sim = float(np.dot(q_emb, c_vec) / denom)
            kw_hits = sum(0.22 for kw in domain_kws if kw in full_txt)
            term_hits = sum(0.10 for t in q_terms if len(t) >= 2 and t in full_txt)
            score = round(max(0.0, min(0.99, cos_sim * 0.55 + kw_hits + term_hits + place_bonus)), 4)

            scored.append(
                {
                    "chunk_id": r["chunk_id"],
                    "doc_id": r["doc_id"],
                    "doc_title": r["doc_title"],
                    "doc_category": r["doc_category"],
                    "standard_code": r["standard_code"] or "",
                    "clause_no": r["clause_no"] or "",
                    "chunk_text": r["chunk_text"],
                    "score": score,
                }
            )

        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[: max(1, top_k)]

    async def stream_chat(
        self,
        messages: List[Dict[str, str]],
        place_type: Optional[str] = None,
        context_summary: Optional[str] = None,
        llm_plugin_enabled: bool = True,
    ) -> AsyncGenerator[str, None]:
        last_user = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), "安全生产合规要求")
        citations = await self.search(last_user, place_type=place_type, top_k=4)

        yield f"data: {json.dumps({'type': 'citations', 'citations': citations}, ensure_ascii=False)}\n\n"

        llm_ready = llm_plugin_enabled and bool(settings.llm_base_url) and (
            "localhost:11434" in settings.llm_base_url or bool(settings.llm_api_key)
        )
        if llm_ready:
            try:
                kb_ctx = "\n".join(
                    [f"[{i+1}] {c['doc_title']} {c['clause_no']}：{c['chunk_text']}" for i, c in enumerate(citations)]
                )
                sys_msg = (
                    "你是 GliHub 3.0 工业安全合规专家助手。请严格依据检索到的国家安全生产法规与国标条款回答问题，"
                    "标注法规名称与条款号，严禁编造法条或篡改确定性数学公式。\n"
                    f"【页面上下文】：{context_summary or '通用合规咨询'}\n"
                    f"【权威法规切片】：\n{kb_ctx}"
                )
                headers = {"Content-Type": "application/json"}
                if settings.llm_api_key:
                    headers["Authorization"] = f"Bearer {settings.llm_api_key}"
                payload = {
                    "model": settings.llm_model,
                    "stream": True,
                    "temperature": 0.2,
                    "messages": [{"role": "system", "content": sys_msg}, *messages[-6:]],
                }
                async with httpx.AsyncClient(timeout=settings.llm_timeout_sec) as client:
                    async with client.stream(
                        "POST", f"{settings.llm_base_url.rstrip('/')}/chat/completions", headers=headers, json=payload
                    ) as resp:
                        if resp.status_code == 200:
                            async for line in resp.aiter_lines():
                                if not line or not line.startswith("data:"):
                                    continue
                                data_str = line[5:].strip()
                                if data_str == "[DONE]":
                                    break
                                chunk_obj = json.loads(data_str)
                                delta = chunk_obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                                if delta:
                                    yield f"data: {json.dumps({'type': 'delta', 'delta': delta}, ensure_ascii=False)}\n\n"
                            yield "data: [DONE]\n\n"
                            return
            except Exception:
                pass

        answer_lines = [
            f"针对您咨询的 **「{last_user[:40]}」**，已从 GliHub 3.0 安全法规库检索到以下权威条款：\n\n"
        ]
        for idx, c in enumerate(citations, start=1):
            std_tag = f"（{c['standard_code']}）" if c["standard_code"] else ""
            answer_lines.append(f"{idx}. **{c['doc_title']}{std_tag} {c['clause_no']}**：{c['chunk_text']}\n")
        answer_lines.append(
            "\n**合规执行建议**：请结合所属场所类别（生产/储存/公辅）将上述标准条款纳入《安全检查表（SCL）》及现场隐患整改验收依据；"
            "如需启用本地 GGUF Q4_K_M 大模型深度推演，可在「AI 模型选装中心」配置 Ollama 或兼容 API。"
        )
        full_reply = "".join(answer_lines)
        for i in range(0, len(full_reply), 20):
            yield f"data: {json.dumps({'type': 'delta', 'delta': full_reply[i : i + 20]}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"


rag_engine = EhsRagEngine()
