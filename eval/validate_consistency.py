# -*- coding: utf-8 -*-
"""
validate_consistency.py —— 一致性验证（任务书：验证评估结果与人工标注的一致程度 / 同一份输出多次评估分数波动）

两类一致性：
  (A) 稳定性：对每份候选运行评估 N 次（LLM 评委 temperature=0.3），统计各维度均值±标准差；
      规则维度应恒定，LLM 维度波动应小。
  (B) 与人工一致：以 human_labels.json 的专家整体分/各维分为基准，
      计算 Spearman 秩相关与平均绝对误差（MAE）。
"""
import os
import sys
import json
import statistics

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.client import Hy3Client
from src.evaluator import evaluate
from src.rubric import DIMENSIONS
from validate_discrimination import spearman


def main():
    here = os.path.dirname(__file__)
    labels = json.load(open(os.path.join(here, "human_labels.json"), encoding="utf-8"))
    paper = open(labels["paper"], encoding="utf-8").read()
    try:
        client = Hy3Client()
    except RuntimeError as e:
        print("⚠️", e)
        client = None

    N = 5
    stability = {}
    eval_overalls = []
    expert_overalls = []
    expert_dim = {d: [] for d in DIMENSIONS}
    eval_dim = {d: [] for d in DIMENSIONS}

    for c in labels["candidates"]:
        note = open(c["note_file"], encoding="utf-8").read()
        runs = [evaluate(paper, note, client, judge_temperature=0.3) for _ in range(N)]
        # 各维度跨次分布
        dim_series = {d: [r["scores"][d] for r in runs] for d in DIMENSIONS}
        means = {d: round(statistics.mean(dim_series[d]), 3) for d in DIMENSIONS}
        stds = {d: round(statistics.pstdev(dim_series[d]), 3) for d in DIMENSIONS}
        stability[c["id"]] = {"mean": means, "std": stds,
                              "overall_mean": round(statistics.mean(r["overall"] for r in runs), 3),
                              "overall_std": round(statistics.pstdev(r["overall"] for r in runs), 3)}
        # 取第 1 次（temp0 近似）作为与专家对比的「正式」评分
        base = runs[0]
        eval_overalls.append(base["overall"])
        expert_overalls.append(c["expected_overall"])
        for d in DIMENSIONS:
            eval_dim[d].append(base["scores"][d])
            expert_dim[d].append(c["expert"][d])
        print(f"  {c['id']:12s} overall={base['overall']} (±{stability[c['id']]['overall_std']}) "
              f"专家={c['expected_overall']}")

    rho_overall = spearman(eval_overalls, expert_overalls)
    dim_mae = {d: round(statistics.mean(abs(eval_dim[d][i] - expert_dim[d][i])
                                        for i in range(len(eval_dim[d]))), 3)
               for d in DIMENSIONS}

    out = {
        "N_runs": N,
        "stability": stability,
        "spearman_vs_expert_overall": round(rho_overall, 3),
        "per_dimension_MAE_vs_expert": dim_mae,
    }
    with open("results/validation_consistency.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"\nSpearman(评估整体分, 专家整体分) = {rho_overall:.3f}")
    print("各维度 MAE（与专家）：", dim_mae)
    print("✅ 一致性验证结果 -> results/validation_consistency.json")


if __name__ == "__main__":
    main()
