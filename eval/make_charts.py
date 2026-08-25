# -*- coding: utf-8 -*-
"""生成评测结果图表（纯 SVG，无需第三方库）。输出到 results/。"""
import json
import os

D = "results"
disc = json.load(open(os.path.join(D, "validation_discrimination.json"), encoding="utf-8"))
cons = json.load(open(os.path.join(D, "validation_consistency.json"), encoding="utf-8"))

# ---- 图1：候选样本 评估整体分 vs 专家预期整体分 ----
cands = disc["per_candidate"]
ids = [c["id"] for c in cands]
ev = [c["overall"] for c in cands]
ex = [c["expected_overall"] for c in cands]

W, H = 720, 360
left, right, top, bottom = 60, 20, 30, 90
plot_w = W - left - right
plot_h = H - top - bottom
ymax = 5.5
def x(i, n, bw):
    return left + (plot_w / n) * i + (plot_w / n - 2 * bw) / 2
def y(v):
    return top + plot_h * (1 - v / ymax)

svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" font-family="sans-serif" font-size="12">']
svg.append(f'<text x="{W//2}" y="18" text-anchor="middle" font-size="14" font-weight="bold">评估整体分 vs 专家预期整体分</text>')
# y 轴
for g in range(0, 6):
    yy = y(g)
    svg.append(f'<line x1="{left}" y1="{yy}" x2="{W-right}" y2="{yy}" stroke="#ddd"/>')
    svg.append(f'<text x="{left-6}" y="{yy+4}" text-anchor="end" fill="#666">{g}</text>')
bw = 16
for i, cid in enumerate(ids):
    xe = x(i, len(ids), bw)
    # 评估分
    h1 = top + plot_h - y(ev[i])
    svg.append(f'<rect x="{xe}" y="{y(ev[i])}" width="{bw}" height="{h1:.1f}" fill="#2f6fed"/>')
    svg.append(f'<text x="{xe+bw/2}" y="{y(ev[i])-4}" text-anchor="middle" font-size="10" fill="#2f6fed">{ev[i]}</text>')
    # 专家分
    h2 = top + plot_h - y(ex[i])
    svg.append(f'<rect x="{xe+bw+4}" y="{y(ex[i])}" width="{bw}" height="{h2:.1f}" fill="#e08a2f"/>')
    svg.append(f'<text x="{xe+bw+4+bw/2}" y="{y(ex[i])-4}" text-anchor="middle" font-size="10" fill="#e08a2f">{ex[i]}</text>')
    svg.append(f'<text x="{xe+bw+2}" y="{H-bottom+16}" text-anchor="middle" font-size="10">{cid}</text>')
svg.append(f'<rect x="{left}" y="{H-22}" width="12" height="12" fill="#2f6fed"/><text x="{left+18}" y="{H-12}" font-size="11">评估分</text>')
svg.append(f'<rect x="{left+90}" y="{H-22}" width="12" height="12" fill="#e08a2f"/><text x="{left+108}" y="{H-12}" font-size="11">专家预期</text>')
svg.append('</svg>')
open(os.path.join(D, "chart_overall.svg"), "w", encoding="utf-8").write("\n".join(svg))

# ---- 图2：各维度 MAE（与专家） ----
mae = cons["per_dimension_MAE_vs_expert"]
labels_cn = {"factual_accuracy":"事实准确性","completeness":"要点完整度","traceability":"证据可追溯性",
             "terminology":"术语正确性","format":"格式规范性","readability":"可读性"}
order = ["factual_accuracy","completeness","traceability","terminology","format","readability"]
W2, H2 = 720, 320
left2, right2, top2, bottom2 = 70, 20, 30, 40
plot_w2 = W2 - left2 - right2
plot_h2 = H2 - top2 - bottom2
vmax = max(mae.values()) + 0.2
def y2(v): return top2 + plot_h2 * (1 - v / vmax)
svg2 = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W2}" height="{H2}" font-family="sans-serif" font-size="12">']
svg2.append(f'<text x="{W2//2}" y="18" text-anchor="middle" font-size="14" font-weight="bold">各维度 MAE（评估分与专家分的平均绝对误差）</text>')
for g in [0, 0.5, 1.0, 1.5]:
    yy = y2(g)
    svg2.append(f'<line x1="{left2}" y1="{yy}" x2="{W2-right2}" y2="{yy}" stroke="#ddd"/>')
    svg2.append(f'<text x="{left2-6}" y="{yy+4}" text-anchor="end" fill="#666">{g}</text>')
bw2 = plot_w2 / len(order) - 24
for i, k in enumerate(order):
    xx = left2 + (plot_w2 / len(order)) * i + 12
    v = mae[k]
    svg2.append(f'<rect x="{xx}" y="{y2(v)}" width="{bw2}" height="{top2+plot_h2 - y2(v):.1f}" fill="#3aa76d"/>')
    svg2.append(f'<text x="{xx+bw2/2}" y="{y2(v)-4}" text-anchor="middle" font-size="10">{v}</text>')
    svg2.append(f'<text x="{xx+bw2/2}" y="{H2-bottom2+16}" text-anchor="middle" font-size="10">{labels_cn[k]}</text>')
svg2.append('</svg>')
open(os.path.join(D, "chart_mae.svg"), "w", encoding="utf-8").write("\n".join(svg2))
print("charts written:", os.path.join(D, "chart_overall.svg"), os.path.join(D, "chart_mae.svg"))
