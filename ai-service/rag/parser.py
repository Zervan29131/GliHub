import re
from pathlib import Path
from typing import Dict, List, Optional
from pypdf import PdfReader


def extract_text_from_file(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        reader = PdfReader(str(file_path))
        pages = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(pages)
    return file_path.read_text(encoding="utf-8", errors="ignore")


def split_legal_clauses(
    raw_text: str,
    applicable_places: str = "production,storage,auxiliary",
) -> List[Dict[str, str]]:
    """
    面向《安全生产法》、GB 国标、危化品 SDS 的结构化条款切分器：
    优先识别「第X条」或「4.1 / 5.2」国标章节号切分，超长段落自动按句号滑窗分段。
    """
    cleaned = re.sub(r"\r\n?", "\n", raw_text).strip()
    if not cleaned:
        return []

    # 剥离简单 HTML 标签（兼容 sys_notice 富文本同步）
    cleaned = re.sub(r"<[^>]+>", "", cleaned)

    pattern = re.compile(r"(?=(?:^|\n)\s*(?:第[一二三四五六七八九十百零\d]+条|\d+\.\d+(?:\.\d+)?)\s*)")
    parts = [p.strip() for p in pattern.split(cleaned) if p and p.strip()]
    if not parts:
        parts = [cleaned]

    chunks: List[Dict[str, str]] = []
    tag_keywords = ["安全帽", "个体防护", "动火", "受限空间", "重大危险源", "储罐", "静电", "安全评价", "隐患", "泄漏", "消防"]

    for idx, part in enumerate(parts, start=1):
        m = re.match(r"^(第[一二三四五六七八九十百零\d]+条|\d+\.\d+(?:\.\d+)?)", part)
        clause_no = m.group(1) if m else f"第{idx}节"
        # 若单条超过 600 字，按 450 字切分
        sub_texts = [part[i : i + 450] for i in range(0, len(part), 450)] if len(part) > 600 else [part]
        for sub_idx, st in enumerate(sub_texts):
            c_no = clause_no if len(sub_texts) == 1 else f"{clause_no}({sub_idx + 1})"
            tags = ",".join([kw for kw in tag_keywords if kw in st])
            chunks.append(
                {
                    "clause_no": c_no,
                    "chunk_text": st.strip(),
                    "applicable_places": applicable_places,
                    "hazard_tags": tags,
                }
            )
    return chunks
