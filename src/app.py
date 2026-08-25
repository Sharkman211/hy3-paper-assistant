# -*- coding: utf-8 -*-
"""
app.py —— 基于 Hy3 的「论文结构化阅读助手」应用侧

场景：真实科研用户（本科生/研究生/算法工程师）在文献调研时，
      需要快速把握一篇论文的「目标-方法-创新-结果-不足」。
为什么需要大模型：论文原文长、专业密度高；结构化抽取 + 领域术语保留
      这类『长文本理解 + 可控格式生成』任务，正适合 LLM，且能显著降低阅读成本。

输出固定 5 板块结构化笔记：
  1. 研究目标  2. 核心方法  3. 主要创新点  4. 实验结果与分析  5. 存在不足与未来方向
"""
import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import argparse
from client import Hy3Client

GENERATE_SYSTEM_PROMPT = """你是专业论文阅读助手，服务于做文献调研的本科生/研究生/算法工程师。
请通读下面的论文（可能是摘要+正文节选），整理一份结构化笔记，严格分为以下 5 个板块，使用 markdown 一级标题：

# 1. 研究目标
- 论文要解决的核心问题、动机与待填补的空白。

# 2. 核心方法
- 完整说明算法/模型/实验方案的关键设计，保留专业术语与缩写（首次出现给出全称）。
- 若存在关键公式或损失/模块，请点出名称与作用。

# 3. 主要创新点
- 本文区别于前人工作的具体贡献，逐条列出。

# 4. 实验结果与分析
- 列出关键指标与对比实验结论（保留具体数值、数据集、基线模型、提升幅度）。
- 区分「本文报告的结果」与「已有方法的结论」。

# 5. 存在不足与未来方向
- 论文自身声明的局限、可优化方向；若原文未明确写明，可基于内容合理推断但需标注「（推断）」。

硬性规则：
1、所有内容必须严格来自原文，禁止编造原文不存在的方法、数值或结论。
2、保留关键专业术语（如 FDR、GO-LSD、BCE、Dice、mAP 等），不滥用同义替换导致歧义。
3、条理清晰、分点书写，避免水话与重复。
4、若原文信息不足以支撑某板块，写「原文未充分提供」，不要臆造。

输出约束：直接给出最终的结构化笔记正文，不要展示思考/分析过程，不要输出任何解释性前缀。
"""


def generate_note(paper_text, client=None, temperature=0.3, max_tokens=6000):
    client = client or Hy3Client()
    return client.chat(GENERATE_SYSTEM_PROMPT, paper_text, temperature=temperature, max_tokens=max_tokens)


def main():
    ap = argparse.ArgumentParser(description="Hy3 论文结构化阅读助手")
    ap.add_argument("--input", "-i", required=True, help="论文文本文件（.txt）")
    ap.add_argument("--output", "-o", default=None, help="笔记输出文件，默认输出到 output/note_<名>.md")
    ap.add_argument("--temperature", type=float, default=0.3)
    args = ap.parse_args()

    with open(args.input, "r", encoding="utf-8") as f:
        paper = f.read()

    client = Hy3Client()
    note = generate_note(paper, client, temperature=args.temperature)

    out_path = args.output
    if not out_path:
        os.makedirs("output", exist_ok=True)
        base = os.path.splitext(os.path.basename(args.input))[0]
        out_path = f"output/note_{base}.md"
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(note)
    print(f"✅ 笔记已生成：{out_path}")


if __name__ == "__main__":
    main()
