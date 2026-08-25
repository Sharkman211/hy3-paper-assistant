# -*- coding: utf-8 -*-
"""
make_demo_gif.py —— 用 Pillow 生成动画 GIF（依赖 Pillow，已安装）。

Pillow 负责 GIF89a 封装与 LZW 编码，输出 100% 兼容各浏览器/系统预览。
演示内容：Hy3 论文阅读助手「输入论文 → 生成 5 板块结构化笔记 → 6 维评估 → 结果」。
单轮时长 < 2 分钟，循环播放。
"""
import os
from PIL import Image, ImageDraw, ImageFont

W, H = 480, 270
BG = (255, 255, 255)
NAVY = (28, 46, 92)
BLUE = (52, 96, 178)
GRAY = (150, 150, 150)
ORANGE = (230, 120, 20)
GREEN = (46, 140, 80)
LIGHT = (235, 240, 250)


def load_font(size, bold=False):
    candidates = [
        'C:/Windows/Fonts/msyh.ttc',
        'C:/Windows/Fonts/simhei.ttf',
        'C:/Windows/Fonts/arialbd.ttf' if bold else 'C:/Windows/Fonts/arial.ttf',
    ]
    for p in candidates:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def new_frame(bg=BG):
    return Image.new('RGB', (W, H), bg)


def bar(d, x, y, w, h, frac, color):
    d.rectangle([x, y + int(h * (1 - frac)), x + w, y + h], fill=color)


def frame_title():
    img = new_frame(NAVY)
    d = ImageDraw.Draw(img)
    f1 = load_font(34, bold=True)
    f2 = load_font(20)
    f3 = load_font(15)
    d.text((W // 2, 78), "Hy3 论文阅读助手", font=f1, fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, 128), "结构化笔记 · Demo", font=f2, fill=(180, 200, 240), anchor="mm")
    d.text((W // 2, 200), "基于 Hy3 大模型 · 自动生成可评估的论文笔记", font=f3,
           fill=(150, 175, 225), anchor="mm")
    return img


def frame_input():
    img = new_frame()
    d = ImageDraw.Draw(img)
    f1 = load_font(22, bold=True)
    f2 = load_font(15)
    d.text((20, 22), "① 输入论文原文", font=f1, fill=NAVY)
    # 论文卡片
    d.rectangle([20, 60, 200, 240], outline=BLUE, width=2, fill=LIGHT)
    d.text((32, 70), "paper.txt", font=f2, fill=BLUE)
    for i in range(9):
        d.line([32, 100 + i * 15, 188, 100 + i * 15], fill=GRAY, width=2)
    # 箭头
    d.line([210, 150, 270, 150], fill=ORANGE, width=3)
    d.polygon([(270, 144), (270, 156), (282, 150)], fill=ORANGE)
    d.text((296, 144), "Hy3", font=load_font(20, bold=True), fill=ORANGE)
    # 右侧说明
    d.text((296, 60), "· 长文理解", font=f2, fill=NAVY)
    d.text((296, 90), "· 要点抽取", font=f2, fill=NAVY)
    d.text((296, 120), "· 可控格式", font=f2, fill=NAVY)
    d.text((296, 150), "· 中文输出", font=f2, fill=NAVY)
    return img


def frame_note():
    img = new_frame()
    d = ImageDraw.Draw(img)
    f1 = load_font(22, bold=True)
    f2 = load_font(15)
    d.text((20, 22), "② Hy3 生成 5 板块结构化笔记", font=f1, fill=NAVY)
    sections = [
        ("1  研究目标", "本文要解决的核心问题与动机"),
        ("2  核心方法", "关键模型 / 算法 / 流程"),
        ("3  主要创新点", "相对已有工作的贡献"),
        ("4  实验结果", "数据集、指标、对比结论"),
        ("5  存在不足", "局限性与未来方向"),
    ]
    y = 58
    for title, desc in sections:
        d.rectangle([20, y, 460, y + 32], fill=LIGHT, outline=BLUE, width=1)
        d.text((30, y + 4), title, font=load_font(15, bold=True), fill=ORANGE)
        d.text((150, y + 8), desc, font=f2, fill=NAVY)
        y += 38
    return img


def frame_eval():
    img = new_frame()
    d = ImageDraw.Draw(img)
    f1 = load_font(22, bold=True)
    f2 = load_font(15)
    d.text((20, 22), "③ 6 维自动评估（规则 + LLM-as-judge）", font=f1, fill=NAVY)
    dims = [
        ("事实准确性", 0.95, GREEN),
        ("要点完整度", 0.90, GREEN),
        ("证据可追溯性", 0.85, BLUE),
        ("术语正确性", 0.92, GREEN),
        ("格式规范性", 1.00, GREEN),
        ("用户可读性", 0.88, BLUE),
    ]
    y = 58
    for name, frac, color in dims:
        d.text((20, y), name, font=f2, fill=NAVY)
        bar(d, 150, y - 2, 250, 16, frac, color)
        d.text((410, y), "%.2f" % frac, font=f2, fill=color)
        y += 32
    return img


def frame_result():
    img = new_frame(NAVY)
    d = ImageDraw.Draw(img)
    f1 = load_font(30, bold=True)
    f2 = load_font(18)
    f3 = load_font(15)
    d.text((W // 2, 60), "评估结果", font=f1, fill=(255, 255, 255), anchor="mm")
    d.text((W // 2, 120), "综合评级：优 A", font=f2, fill=ORANGE, anchor="mm")
    d.text((W // 2, 165), "Overall Score：4.85 / 5.00", font=f2, fill=(200, 215, 245), anchor="mm")
    d.text((W // 2, 215), "判别力 / 一致性 / 对抗性 三项验证通过", font=f3,
           fill=(160, 185, 230), anchor="mm")
    return img


def main():
    frames = [
        frame_title(),
        frame_input(),
        frame_note(),
        frame_eval(),
        frame_result(),
    ]
    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "demo.gif")
    frames[0].save(
        out_path,
        save_all=True,
        append_images=frames[1:],
        duration=900,        # 每帧 0.9 秒
        loop=0,              # 0 = 无限循环
        disposal=2,
        optimize=True,
    )
    total = 900 * len(frames) / 1000.0
    print("✅ demo.gif 已生成：%s  帧数=%d  单轮=%.1fs 尺寸=%dx%d"
          % (out_path, len(frames), total, W, H))


if __name__ == "__main__":
    main()
