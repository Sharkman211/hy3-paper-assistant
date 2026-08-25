# -*- coding: utf-8 -*-
"""
validate_discrimination.py —— 判别力验证（任务书：构造质量明显差异的输出，验证评估方法能否正确区分并排序）

对 human_labels.json 中的 6 个候选（good/medium/bad + 3 个对抗），
调用混合评估器得到整体分，与专家预期整体分/排名比较：
  - 计算 Spearman 秩相关（自动排序能力）；
  - 验证 good > medium > bad 的单调关系是否成立。
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.client import Hy3Client
from src.evaluator import evaluate
from src.rubric import DIMENSIONS


def spearman(a, b):
    """a,b 等长数值列表，返回 Spearman 秩相关（含相等秩的平均秩）。"""
    def rank(x):
        s = sorted(range(len(x)), key=lambda i: x[i])
        r = [0] * len(x)
        i = 0
        while i < len(s):
            j = i
            while j + 1 < len(s) and x[s[j + 1]] == x[s[i]]:
                j += 1
            avg = (i + j) / 2.0 + 1
            for k in range(i, j + 1):
                r[s[k]] = avg
            i = j + 1
        return r
    ra, rb = rank(a), rank(b)
    n = len(a)
    d2 = sum((ra[i] - rb[i]) ** 2 for i in range(n))
    return 1 - 6 * d2 / (n * (n ** 2 - 1))


def main():
    here = os.path.dirname(__file__)
    labels = json.load(open(os.path.join(here, "human_labels.json"), encoding="utf-8"))
    paper = open(labels["paper"], encoding="utf-8").read()
    try:
        client = Hy3Client()
    except RuntimeError as e:
        print("⚠️", e)
        client = None

    results = []
    for c in labels["candidates"]:
        note = open(c["note_file"], encoding="utf-8").read()
        res = evaluate(paper, note, client)
        results.append({
            "id": c["id"], "tier": c["tier"],
            "overall": res["overall"],
            "expected_overall": c["expected_overall"],
            "expected_rank": c["expected_rank"],
            "scores": res["scores"],
        })
        print(f"  {c['id']:12s} 评估整体={res['overall']}  专家预期={c['expected_overall']}")

    eval_overall = [r["overall"] for r in results]
    exp_overall = [r["expected_overall"] for r in results]
    rho = spearman(eval_overall, exp_overall)

    # 单调关系 good > medium > bad
    m = {r["id"]: r["overall"] for r in results}
    monotonic_ok = (m["good"] > m["medium"] > m["bad"])

    out = {
        "spearman_vs_expert": round(rho, 3),
        "good_gt_medium_gt_bad": monotonic_ok,
        "per_candidate": results,
    }
    with open("results/validation_discrimination.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSpearman(评估分, 专家预期) = {rho:.3f}")
    print(f"good > medium > bad 单调成立：{monotonic_ok}")
    print("✅ 判别力验证结果 -> results/validation_discrimination.json")


if __name__ == "__main__":
    main()
