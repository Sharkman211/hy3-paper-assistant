# -*- coding: utf-8 -*-
"""
run_eval.py —— 完整评测执行（任务书：在自构建的评测样本集上完成一次完整评测）

对 dataset/papers/ 下每篇论文：
  1) 调用 Hy3 生成结构化笔记（应用侧）；
  2) 调用混合评估器打分；
  3) 落盘笔记与评测结果。
最终汇总为 results/result_table.csv、results/summary.json、results/case_analysis.md。

用法：python eval/run_eval.py
"""
import os
import sys
import csv
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.client import Hy3Client
from src.app import generate_note
from src.evaluator import evaluate
from src.rubric import DIMENSIONS, DIMENSION_LABELS, score_to_grade

PAPER_DIR = "dataset/papers"
NOTE_DIR = "output"
RESULTS_DIR = "results"
SUMMARY = os.path.join(RESULTS_DIR, "summary.json")
TABLE = os.path.join(RESULTS_DIR, "result_table.csv")
CASE = os.path.join(RESULTS_DIR, "case_analysis.md")


def load_papers():
    out = []
    for fn in sorted(os.listdir(PAPER_DIR)):
        if fn.lower().endswith(".txt"):
            with open(os.path.join(PAPER_DIR, fn), encoding="utf-8") as f:
                out.append((fn, f.read()))
    return out


def main():
    os.makedirs(NOTE_DIR, exist_ok=True)
    os.makedirs(RESULTS_DIR, exist_ok=True)
    try:
        client = Hy3Client()
    except RuntimeError as e:
        print("⚠️", e)
        client = None

    papers = load_papers()
    print(f"检测到 {len(papers)} 篇论文，开始生成笔记并评测……")
    records = []
    for fn, text in papers:
        pid = fn.rsplit(".", 1)[0]
        print(f"\n===== {pid} =====")
        try:
            note = generate_note(text, client, temperature=0.3, max_tokens=3096)
        except Exception as e:
            print(f"  ⚠️ 笔记生成失败，跳过该样本：{e}")
            continue
        if not note or not note.strip():
            print(f"  ⚠️ 笔记为空，跳过该样本（疑似接口受限）")
            continue
        note_path = os.path.join(NOTE_DIR, f"note_{pid}.md")
        with open(note_path, "w", encoding="utf-8") as f:
            f.write(note)
        res = evaluate(text, note, client)
        rec = {
            "paper_id": pid,
            "overall": res["overall"],
            "grade": res["grade"],
            "mode": res["mode"],
            "scores": res["scores"],
            "evidence": res["evidence"],
            "comment": res["comment"],
            "fabricated_citations": res["fabricated_citations"],
            "note_path": note_path,
        }
        records.append(rec)
        print(f"  整体分={res['overall']} ({res['grade']}) 维度={res['scores']}")

    # 汇总 CSV
    with open(TABLE, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["paper_id", "overall", "grade", "mode"] +
                   DIMENSIONS + ["fabricated_citations", "comment"])
        for r in records:
            row = [r["paper_id"], r["overall"], r["grade"], r["mode"]]
            row += [r["scores"][d] for d in DIMENSIONS]
            row += [",".join(r["fabricated_citations"]), r["comment"].replace("\n", " ")]
            w.writerow(row)

    with open(SUMMARY, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    # 典型 case 归因
    write_case_analysis(records, CASE)
    print(f"\n✅ 完整评测完成：{TABLE}, {SUMMARY}, {CASE}")


def write_case_analysis(records, path):
    # 最优 / 最劣
    ranked = sorted(records, key=lambda r: r["overall"], reverse=True)
    best, worst = ranked[0], ranked[-1]
    lines = ["# 典型 Case 归因分析\n"]
    lines.append(f"共评测 {len(records)} 篇。整体分区间："
                 f"{worst['overall']} ~ {best['overall']}。\n")

    def block(r, tag):
        lines.append(f"## {tag}：{r['paper_id']}（整体 {r['overall']} / {r['grade']}）\n")
        lines.append("- 各维度分：" +
                     "，".join(f"{DIMENSION_LABELS[d]}={r['scores'][d]}" for d in DIMENSIONS))
        ev = r["evidence"]
        lines.append(f"- 格式证据：命中标题 {ev['format'].get('sections_hit')}/5")
        lines.append(f"- 完整度证据：命中板块 {ev['completeness'].get('sections_hit')}/5")
        lines.append(f"- 可追溯性证据：trace_ratio={ev['traceability'].get('trace_ratio')}")
        if r["fabricated_citations"]:
            lines.append(f"- ⚠️ 检测到疑似伪造引用：{r['fabricated_citations']}")
        lines.append(f"- 评测评语：{r['comment']}\n")

    block(best, "最优样本")
    block(worst, "最弱样本")
    # 中间取一个
    if len(ranked) >= 3:
        block(ranked[len(ranked) // 2], "中间样本")

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


if __name__ == "__main__":
    main()
