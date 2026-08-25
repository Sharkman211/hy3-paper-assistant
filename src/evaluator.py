# -*- coding: utf-8 -*-
"""
evaluator.py —— 混合评估器（规则校验 + LLM-as-judge）

设计依据（任务书：说明选择该方式的设计依据）：
  * 客观、可程序化校验的维度 → 规则（deterministic，零成本、可复现、可解释）：
      - 格式规范性 format：检测 5 个规定标题是否出现、是否 markdown 分点。
      - 要点完整度 completeness：检测 5 个板块命中数。
      - 证据可追溯性 traceability：以「论断句关键词/数字/4-gram 与原文重叠率」近似度量。
  * 需要语义理解的主观维度 → LLM-as-judge（Hy3）：
      - 事实准确性 factual_accuracy：需对照原文逐条核对数字/方法/结论是否被编造。
      - 专业术语正确性 terminology：需判断缩写映射、张冠李戴、生造术语。
      - 可读性 readability：需整体把握行文流畅度与逻辑。
  规则负责「可核对」，LLM 负责「需理解」，二者互补；
  同时规则产出可解释证据（命中了哪些标题、trace_ratio 多少），便于失败归因。

降级模式（无 API key / 离线）：factual_accuracy 与 terminology 用规则近似，
并在结果中标注 mode='rule_fallback'，明确其仅为离线演示，正式评测以 Hy3 为准。
"""
import os
import re
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import json
from rubric import (
    DIMENSIONS, DIMENSION_LABELS, RUBRIC, WEIGHTS,
    REQUIRED_SECTIONS, overall_score, score_to_grade,
)

# ----------------------------- 工具 -----------------------------
# 板块→匹配关键词（用于宽松但稳定的标题命中，避免『实验结果』≠『实验结果与分析』漏判）
SECTION_KEYWORDS = {
    "研究目标": ["研究目标", "研究目的", "目标"],
    "核心方法": ["核心方法", "方法", "模型"],
    "主要创新点": ["创新点", "主要创新", "贡献"],
    "实验结果与分析": ["实验结果", "实验", "结果"],
    "存在不足与未来方向": ["不足", "局限", "未来方向", "未来工作"],
}


def _detect_sections(note):
    """返回 (命中板块集合, 所有标题文本列表)。"""
    found = set()
    headers = []
    for line in note.splitlines():
        m = re.match(r"^\s*#{1,6}\s*(.+?)\s*$", line)
        if m:
            headers.append(m.group(1).strip())
            continue
        m = re.match(r"^\s*\d+\s*[\.、]\s*(.+?)\s*$", line)
        if m:
            headers.append(m.group(1).strip())
    for sec, kws in SECTION_KEYWORDS.items():
        for h in headers:
            if any(kw in h for kw in kws):
                found.add(sec)
                break
    return found, headers


def _sentences(text):
    """按中英文句末与换行切分句子。"""
    parts = re.split(r"[。！？\n;]", text)
    out = []
    for p in parts:
        p = p.strip()
        if p:
            out.append(p)
    return out


_NUM_RE = re.compile(r"\d+\.\d+%?|\d+%|\d+")
_LAT_RE = re.compile(r"[A-Za-z][A-Za-z0-9+]*")


def _signals(sentence):
    """抽取一个句子的『可溯源信号』：数字 + 长度≥3 的拉丁词 + 中文 4-gram。"""
    nums = _NUM_RE.findall(sentence)
    lats = [w for w in _LAT_RE.findall(sentence) if len(w) >= 3]
    zh = re.findall(r"[一-鿿]", sentence)
    grams = []
    if len(zh) >= 4:
        grams = ["".join(zh[i:i+4]) for i in range(len(zh) - 3)]
    return nums, lats, grams


def _trace_ratio(paper, note):
    """计算笔记『事实论断句』与原文的信号重叠率（0-1）。

    设计：仅对含有具体信号（数字 / 长度≥3 的拉丁术语）的句子做可追溯性校验；
    纯中文阐述句（无线索信号）视为中性、不计入，避免对合理概括过度惩罚。
    对含伪造数字/术语的句子，其信号在原文中缺失 → 重叠率下降，从而被识别。
    """
    paper_lower = paper.lower()
    sentences = _sentences(note)
    ratios = []
    for s in sentences:
        if len(s) < 6:
            continue
        nums, lats, grams = _signals(s)
        # 仅校验「含具体事实信号」的句子
        if not (nums or lats):
            continue
        checks = []
        checks += [n in paper for n in nums]
        checks += [w.lower() in paper_lower for w in lats]
        if not checks:
            continue
        ratios.append(sum(checks) / len(checks))
    if not ratios:
        return 0.0
    return sum(ratios) / len(ratios)


# ----------------------------- 规则评分 -----------------------------
def rule_format(note):
    found, headers = _detect_sections(note)
    h = len(found)
    # 是否有分点（'-' 或 '*' 列表）
    has_bullets = bool(re.search(r"^\s*[-*]\s+", note, re.M))
    score = {5: 5, 4: 4, 3: 3, 2: 2, 1: 1, 0: 0}.get(h, 0)
    if h == 5 and not has_bullets:
        score = 4
    return score, {"sections_hit": h, "has_bullets": has_bullets, "hit": list(found)}


def rule_completeness(note):
    found, _ = _detect_sections(note)
    h = len(found)
    score = {5: 5, 4: 4, 3: 3, 2: 2, 1: 1, 0: 0}.get(h, 0)
    # 若 5 板块齐全但『实验结果』板块没有任何数字，则降级（缺关键子要点）
    if h == 5:
        exp = _section_text(note, "实验结果与分析")
        if not _NUM_RE.search(exp or ""):
            score = 4
    return score, {"sections_hit": h, "hit": list(found)}


def _section_text(note, section_name):
    """抽取某板块的正文（到下一个标题前）。"""
    lines = note.splitlines()
    buf = []
    capturing = False
    for line in lines:
        m = re.match(r"^\s*#{1,6}\s*(.+?)\s*$", line) or re.match(r"^\s*\d+\s*[\.、]\s*(.+?)\s*$", line)
        if m:
            title = m.group(1).strip()
            if section_name in title:
                capturing = True
                continue
            elif capturing:
                break
        if capturing:
            buf.append(line)
    return "\n".join(buf)


def rule_traceability(paper, note):
    ratio = _trace_ratio(paper, note)
    if ratio >= 0.90:
        s = 5
    elif ratio >= 0.80:
        s = 4
    elif ratio >= 0.65:
        s = 3
    elif ratio >= 0.50:
        s = 2
    elif ratio > 0.0:
        s = 1
    else:
        s = 0
    return s, {"trace_ratio": round(ratio, 3)}


# ----------------------------- 伪造引用检测（对抗验证专用） -----------------------------
def detect_fabricated_citations(paper, note):
    """检测笔记中出现的引用标记是否在原文中可找到；返回疑似伪造引用列表。"""
    # 抽取笔记中的引用样式：[n]、arXiv:xxxx、et al.、(Author, Year)
    cite_patterns = [
        r"\[(\d{1,3})\]",                     # [12]
        r"arXiv[: ]?(\d{4}\.\d{4,5})",        # arXiv:2005.12872
        r"([A-Z][a-z]+)\s+et\s+al\.",         # Carion et al.
    ]
    suspicious = []
    for pat in cite_patterns:
        for m in re.finditer(pat, note):
            token = m.group(0)
            if token not in paper:
                suspicious.append(token)
    return suspicious


# ----------------------------- LLM-as-judge -----------------------------
JUDGE_SYSTEM_PROMPT = """你是严谨的论文笔记评测专家。请对照【论文原文】与【AI 笔记】，
对笔记从 3 个维度打分（每个 0-5 整数），并给出简短中文评语。

维度与锚点（务必按锚点判定，避免模糊）：
【事实准确性】
5=全部论断原文可查、零编造；4=≥90% 可溯源、≤1 处轻微改写偏差；3=约75-90%可溯源、1-2处概括偏差；
2=约50-75%可溯源、局部臆测但核心结论正确；1=<50%可溯源、含编造结论/伪造数值；0=大面积虚构。
【专业术语正确性】
5=术语/缩写准确；3=1-2 处术语错误；1=大量术语错误或生造；0=术语普遍错误。
【可读性】
5=通顺连贯、重点突出；3=基本可读但有费解处；1=大量病句难读；0=混乱不可读。

只返回标准 JSON（不要代码块、不要多余文字），字段：
factual_accuracy, terminology, readability, comment

输出约束：直接返回最终 JSON，不要展示思考/分析过程。
"""


def llm_judge(paper, note, client, temperature=0.0):
    user = f"【论文原文】\n{paper}\n\n【AI 笔记】\n{note}"
    data = client.chat_json(JUDGE_SYSTEM_PROMPT, user, temperature=temperature, max_tokens=800)
    # 规整到 0-5 整数
    out = {}
    for k in ("factual_accuracy", "terminology", "readability"):
        v = data.get(k)
        try:
            out[k] = max(0, min(5, int(round(float(v)))))
        except (TypeError, ValueError):
            out[k] = None
    out["comment"] = data.get("comment", "")
    return out


# ----------------------------- 降级模式（无 API） -----------------------------
def rule_fallback_judge(paper, note):
    """离线近似：事实准确性≈由可追溯性+无伪造引用近似；术语正确性≈由术语是否在原文出现近似。"""
    tr = rule_traceability(paper, note)[0]
    fab = detect_fabricated_citations(paper, note)
    factual = max(0, min(5, int(round(tr * 4 + (0 if fab else 1))))
                  ) if tr > 0 else 0
    if fab:
        factual = max(0, factual - 2)
    # 术语：笔记中长度>=4 的拉丁词若大量不在原文，视为疑似术语错误
    lats = set(w for w in _LAT_RE.findall(note) if len(w) >= 4)
    if lats:
        missing = sum(1 for w in lats if w.lower() not in paper.lower())
        ratio_missing = missing / len(lats)
        terminology = 5 if ratio_missing < 0.1 else (3 if ratio_missing < 0.3 else 1)
    else:
        terminology = 4
    readability = 4  # 离线无法判读，给中性值并标注
    return {"factual_accuracy": factual, "terminology": terminology,
            "readability": readability, "comment": "【rule_fallback 模式】未调用 LLM，分数为规则近似，仅供离线演示。"}


# ----------------------------- 总入口 -----------------------------
def evaluate(paper, note, client=None, judge_temperature=0.0):
    """
    返回 dict：
      mode: 'llm' 或 'rule_fallback'
      scores: {维度: 0-5}
      overall: 加权整体分
      grade: 等级
      evidence: 规则证据
      comment: LLM 评语
      fabricated_citations: 疑似伪造引用（若有）
    """
    fmt_s, fmt_ev = rule_format(note)
    comp_s, comp_ev = rule_completeness(note)
    trace_s, trace_ev = rule_traceability(paper, note)
    fab = detect_fabricated_citations(paper, note)

    if client is not None:
        try:
            j = llm_judge(paper, note, client, temperature=judge_temperature)
            mode = "llm"
        except Exception as e:
            j = rule_fallback_judge(paper, note)
            mode = "rule_fallback"
            j["comment"] = f"（LLM 调用失败，降级规则近似：{e}）" + j["comment"]
    else:
        j = rule_fallback_judge(paper, note)
        mode = "rule_fallback"

    scores = {
        "factual_accuracy": j["factual_accuracy"],
        "completeness": comp_s,
        "traceability": trace_s,
        "terminology": j["terminology"],
        "format": fmt_s,
        "readability": j["readability"],
    }
    # 若 LLM 维度返回 None（解析异常），用规则近似兜底
    for k in ("factual_accuracy", "terminology", "readability"):
        if scores[k] is None:
            scores[k] = rule_fallback_judge(paper, note)[k]

    overall = overall_score(scores)
    return {
        "mode": mode,
        "scores": scores,
        "overall": overall,
        "grade": score_to_grade(overall),
        "evidence": {"format": fmt_ev, "completeness": comp_ev, "traceability": trace_ev},
        "comment": j.get("comment", ""),
        "fabricated_citations": fab,
    }


if __name__ == "__main__":
    import sys
    if len(sys.argv) >= 3:
        with open(sys.argv[1], encoding="utf-8") as f:
            paper = f.read()
        with open(sys.argv[2], encoding="utf-8") as f:
            note = f.read()
        from client import Hy3Client
        try:
            client = Hy3Client()
        except RuntimeError:
            client = None
        res = evaluate(paper, note, client)
        print(json.dumps(res, ensure_ascii=False, indent=2))
