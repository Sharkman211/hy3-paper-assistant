# hy3-paper-assistant · 论文结构化阅读助手 + 自定义评估方法

> 基于 **Hy3（腾讯混元 HY-3）** 构建一个面向真实用户场景的 AI 应用（学术方向：论文阅读助手），
> 并自行设计、实现、验证了面向该开放场景的评估方法。


---

## 1. 项目介绍

### 1.1 这是什么
一个**基于大模型的论文结构化阅读助手**：给定一篇论文文本，自动产出一份固定 5 板块的结构化笔记，
帮助科研用户在文献调研时快速把握一篇论文的脉络。

### 1.2 目标用户与待解决的问题
- **目标用户**：做文献调研的本科生 / 研究生 / 算法工程师。
- **待解决问题**：论文原文长、专业密度高，逐篇精读成本高、耗时长；且不同人整理的笔记质量参差、难以横向比较。
- **引入大模型的必要性**：「长文本理解 + 可控格式生成 + 术语保留」这类任务正适合 LLM，能在秒级产出
  统一结构、保留关键术语与数值的笔记，显著降低阅读与归纳成本。

### 1.3 输出结构（5 板块）
1. 研究目标　2. 核心方法　3. 主要创新点　4. 实验结果与分析　5. 存在不足与未来方向

### 1.4 评估方法（自行设计）
针对「无唯一标准答案」的开放场景，设计 **6 个维度、0–5 分、带可操作锚点** 的评估 rubric，并采用
**规则校验 + LLM-as-judge 混合** 的自动/半自动评测流程：

| 维度 | 评估方式 | 说明 |
|---|---|---|
| 事实准确性 | LLM-as-judge | 需逐条核对数字/方法/结论是否被编造 |
| 要点完整度 | 规则 | 检测 5 板块命中数 |
| 证据可追溯性 | 规则 | 论断句信号与原文重叠率 |
| 专业术语正确性 | LLM-as-judge | 判断缩写/术语是否张冠李戴、生造 |
| 格式规范性 | 规则 | 检测标题与 markdown 分点 |
| 用户可读性 | LLM-as-judge | 整体行文流畅度与逻辑 |

整体分 = Σ(维度分 × 权重)，权重见 `src/rubric.py`。无 API 密钥时自动降级为 `rule_fallback` 模式，流程仍可演示。

---

## 2. 环境要求

| 项目 | 要求 |
|---|---|
| Python | **≥ 3.8**（已在 3.13 验证） |
| 操作系统 | Windows / macOS / Linux 均可 |
| 核心依赖 | **仅 Python 标准库**（`urllib` / `json` / `re` 等），**无需**安装任何第三方包即可运行应用与评测 |
| 可选依赖（仅用于生成 Demo） | `pillow`、`imageio`、`imageio-ffmpeg`（见第 4 节） |
| 运行密钥 | 一个可用的 **Hy3 OpenAI 兼容端点**（API_KEY / BASE_URL / MODEL_NAME） |
| 网络 | 调用 Hy3 时需联网；无密钥可离线演示（降级模式） |


### 2.1 配置密钥
项目从仓库根目录的 `.env` 读取配置（代码自带解析，无需 `python-dotenv`）。
1. 复制样例：`cp config.example.env .env`
2. 编辑 `.env` 填入你的端点：
   ```env
   API_KEY=你的Hy3密钥
   BASE_URL=https://你的Hy3网关/v1
   MODEL_NAME=hy3
   ```

---

## 3. 目录结构
```
src/
  client.py        Hy3 OpenAI 兼容客户端（标准库 urllib 实现）
  app.py           论文阅读助手（生成五板块笔记）
  rubric.py        6 维度评估定义与可操作锚点、权重
  evaluator.py     混合评估器（规则校验 + LLM-as-judge + 离线降级）
eval/
  run_eval.py               完整评测执行（生成笔记+打分，输出结果表）
  validate_discrimination.py  判别力验证
  validate_consistency.py     一致性验证（稳定性 + 与人工一致）
  validate_adversarial.py     对抗性验证
  human_labels.json          专家参考标注（人工基准）
  METHOD.md                  评估方法说明文档（6 维锚点/权重/规则+LLM-judge/验证设计）
  make_charts.py             结果图表（SVG）
dataset/
  papers/          7 篇跨领域输入论文（CV×4：YOLO26 / DenseDETR / 航拍小目标 / D-FINE-SEG；NLP / 医学 / 金融）
  candidates/      好/中/差 + 3 个对抗候选样本（notes/）
  sample_set.md    评测样本集说明（来源/构造/覆盖/难例占比）
results/           结果表、汇总 JSON、典型 case 归因、验证 JSON、图表
output/           评测生成的 7 篇结构化笔记样例（markdown）
report/
  analysis_report.md  分析报告（场景/方案/维度依据/结论/失败模式/典型模式）
demo/
  demo.mp4 / demo.gif / demo.html   演示（≤ 2 分钟）
  make_demo_video.py / make_demo_gif.py   生成脚本
```

---

## 4. 运行方式

> 以下命令均在**仓库根目录** `hy3-paper-assistant/` 下执行。
> 应用脚本通过 `sys.path` 自动定位 `src/`，因此请使用 `python src/app.py ...` 形式（不要加 `-m`）。

### 4.1 一键完成全部评测与验证
```bash
cp config.example.env .env        # 填入 Hy3 密钥（无密钥也能跑，自动降级）
python eval/run_eval.py                  # 完整评测：7 篇论文生成+打分 → results/
python eval/validate_discrimination.py   # 判别力验证
python eval/validate_consistency.py      # 一致性验证（稳定性 + 与人工一致）
python eval/validate_adversarial.py      # 对抗性验证
python eval/make_charts.py               # 生成结果图表（SVG）
```

### 4.2 单独运行应用（生成一篇笔记）
```bash
# 必填 --input（论文 txt）；--output 可选，默认写到 output/note_<名>.md
python src/app.py --input dataset/papers/paper_dfineseg.txt --output output/note_demo.md
```

### 4.3 单独评估一篇已有笔记
```bash
# 位置参数：<论文原文> <笔记文件>
python src/evaluator.py dataset/paper.txt output/note_demo.md
```

### 4.4 （可选）重新生成演示视频 / 动图
```bash
pip install pillow imageio imageio-ffmpeg   # 仅首次需要
python demo/make_demo_video.py    # 生成 demo/demo.mp4（约 56 秒，H.264）
python demo/make_demo_gif.py      # 生成 demo/demo.gif（循环动画）
```

### 4.5 查看结果
- 评测结果表格 / 汇总：`results/result_table.csv`、`results/summary.json`
- 验证数据：`results/validation_*.json`
- 分析报告：`report/analysis_report.md`
- 演示：`demo/demo.mp4`、`demo/demo.gif`（或浏览器打开 `demo/demo.html`）

---

## 5. 关键结论（真实运行）
- 完整评测 7 篇跨领域论文：整体 4.6–5.0，6 篇达「优 A」、1 篇（医学）「良 B」，详见 `results/result_table.csv`。
- 判别力：Spearman(评估, 专家) = **0.886**，good > medium > bad 单调成立。
- 一致性：5 次重复评估整体分 std 多为 0（可复现）；与专家 Spearman = **0.814**。
- 对抗性：堆篇幅 / 堆术语 / 伪造引用 **三项均被识别**。
- 失败模式与能力边界分析见 `report/analysis_report.md` 第 5 节。

## 6. 交付内容对照（任务书 5 大类）

本仓库根目录即为完整提交包；逐条对照见 `交付清单.md`。速览：

| 任务书要求 | 对应位置 |
|---|---|
| 一、开源项目仓库（应用源码 / README / 环境样例 / 运行说明） | `src/` · `README.md` · `config.example.env` · `requirements.txt` |
| 二、评测材料（样本集 / 方法说明 / 脚本 / 完整结果表格） | `dataset/` · `eval/METHOD.md` · `eval/*.py` · `results/result_table.csv` |
| 三、有效性验证结果（实验过程与数据） | `results/validation_*.json` · `results/case_analysis.md` |
| 四、分析报告（场景 / 方案 / 维度依据 / 结论 / 失败模式 / 典型模式） | `report/analysis_report.md` |
| 五、Demo（≤ 2 分钟） | `demo/demo.mp4` · `demo/demo.gif` · `demo/demo.html` |

