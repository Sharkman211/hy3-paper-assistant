# -*- coding: utf-8 -*-
"""
validate_adversarial.py —— 对抗性验证（任务书：鼓励额外完成对抗性验证）

检验评估方法是否会被『堆篇幅 / 堆术语 / 伪造引用』等手段抬高评分：
  - adv_padding：内容正确但大量冗余填充 → 评估整体分不应高于 good（长度无奖励）。
  - adv_jargon：生造大量术语 → terminology 维度应显著低于 good，整体不被高估。
  - adv_cite：伪造引用与数值 → 应被 detect_fabricated_citations 捕获，factual 维度被拉低。
每项给出 pass/fail 与证据。
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from src.client import Hy3Client
from src.evaluator import evaluate
from src.rubric import DIMENSION_LABELS


def main():
    here = os.path.dirname(__file__)
    labels = json.load(open(os.path.join(here, "human_labels.json"), encoding="utf-8"))
    paper = open(labels["paper"], encoding="utf-8").read()
    try:
        client = Hy3Client()
    except RuntimeError as e:
        print("⚠️", e)
        client = None

    cand = {c["id"]: c for c in labels["candidates"]}
    res = {}
    for cid in ["good", "adv_padding", "adv_jargon", "adv_cite"]:
        c = cand[cid]
        note = open(c["note_file"], encoding="utf-8").read()
        r = evaluate(paper, note, client)
        res[cid] = {"overall": r["overall"], "scores": r["scores"],
                    "fabricated_citations": r["fabricated_citations"],
                    "char_len": len(note)}

    good = res["good"]
    checks = []

    # 1) 堆篇幅
    pad = res["adv_padding"]
    checks.append({
        "name": "堆篇幅不抬高评分",
        "detail": f"adv_padding 字数={pad['char_len']}（good={good['char_len']}），"
                  f"整体分={pad['overall']} vs good={good['overall']}",
        "pass": pad["overall"] <= good["overall"],
    })

    # 2) 堆术语
    jg = res["adv_jargon"]
    checks.append({
        "name": "堆术语不被误判高质量",
        "detail": f"adv_jargon terminology={jg['scores']['terminology']} vs good={good['scores']['terminology']}；"
                  f"整体分={jg['overall']}",
        "pass": jg["scores"]["terminology"] < good["scores"]["terminology"] and jg["overall"] < good["overall"],
    })

    # 3) 伪造引用/数值
    ct = res["adv_cite"]
    checks.append({
        "name": "伪造引用/数值被捕获并扣分",
        "detail": f"检测到伪造引用={ct['fabricated_citations']}；"
                  f"factual={ct['scores']['factual_accuracy']} vs good={good['scores']['factual_accuracy']}；"
                  f"整体分={ct['overall']}",
        "pass": (len(ct["fabricated_citations"]) > 0) and (ct["scores"]["factual_accuracy"] < good["scores"]["factual_accuracy"]),
    })

    out = {"checks": checks, "all_pass": all(c["pass"] for c in checks)}
    with open("results/validation_adversarial.json", "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    for c in checks:
        print(f"  [{'PASS' if c['pass'] else 'FAIL'}] {c['name']} —— {c['detail']}")
    print(f"\n对抗性验证全部通过：{out['all_pass']}")
    print("✅ 对抗性验证结果 -> results/validation_adversarial.json")


if __name__ == "__main__":
    main()
