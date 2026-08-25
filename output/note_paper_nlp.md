# 1. 研究目标
- 核心问题：低资源语言对（如斯瓦希里语-英语）因平行语料稀缺，神经机器翻译（NMT）性能明显受限，模型易过拟合且词表外（OOV）严重。
- 动机：回译（Back-Translation, BT）可用单语目标语数据生成伪平行对，但随机混合伪数据与真实数据会引入噪声。
- 待填补空白：假设按难度课程化地引入伪数据可稳定训练，需设计有效的课程调度机制以利用回译合成数据提升低资源 NMT。

# 2. 核心方法
- 整体方案 BT-Curriculum：在回译（Back-Translation, BT）生成合成平行句对的基础上，引入课程学习（Curriculum Learning）调度，按「句子长度-词表覆盖率」两维难度对训练样本排序，从易到难逐步训练。
- 回译（Back-Translation, BT）：用目标语单语数据经反向模型生成源语句，构成伪平行对。
- 难度度量：对每条样本计算难度 d = α·len_norm + β·(1 - vocab_cov)，其中 len_norm 为长度归一化（length normalization），vocab_cov 为该句在共享词表中的覆盖比例（vocabulary coverage）。该公式作用为量化样本难度，结合句子长度和词表覆盖率。
- 课程调度（Curriculum Scheduling）：训练分 K=5 个阶段，阶段 k 仅使用难度最低的 (k/K) 比例样本（含全部真实平行对），每阶段固定轮数后进入下一阶段。作用是从易到难逐步训练，稳定训练过程。

# 3. 主要创新点
- 提出 BT-Curriculum 框架，将回译（Back-Translation）与课程学习（Curriculum Learning）结合，用于低资源神经机器翻译。
- 设计基于「句子长度-词表覆盖率」两维的难度度量公式 d = α·len_norm + β·(1 - vocab_cov)（首次给出全称：长度归一化 len_norm、词表覆盖率 vocab_cov）。
- 设计分阶段课程调度策略（K=5），每个阶段仅使用难度最低的 (k/K) 比例样本且包含全部真实平行对，实现从易到难逐步训练，区别于随机混合回译（Rand-BT）基线。

# 4. 实验结果与分析
- 数据集：TED talks sw-en（仅 23k 平行对）、ro-en（78k 平行对），单语目标语各 2M 句。
- 本文报告的结果（BT-Curriculum，BLEU 为 sacreBLEU 去重后）：
  - sw-en: 35.1 BLEU；ro-en: 34.9 BLEU。
  - OOV 率 >15% 的子集上，BT-Curriculum 相对 Rand-BT 提升达 3.0 BLEU。
  - 消融实验：去掉课程调度（仅回译）下降 1.9 BLEU；K=3 与 K=5 差异 <0.3。
- 已有方法的结论（基线模型结果，由本文报告用于对比）：
  - 标准 Transformer-base：sw-en 21.3 BLEU，ro-en 28.4 BLEU。
  - 随机混合回译（Rand-BT）：sw-en 33.0 BLEU，ro-en 33.2 BLEU。
  - 对比结论：BT-Curriculum 相比 Rand-BT 在 sw-en 提升 2.1 BLEU（35.1 vs 33.0），在 ro-en 提升 1.7 BLEU（34.9 vs 33.2）；且对 OOV 率高的语言对提升更明显（摘要指出）。

# 5. 存在不足与未来方向
- 局限（论文声明）：反向模型质量本身依赖少量平行对，极端低资源（<5k）下增益收窄。
- 局限（论文声明）：课程难度度量未考虑句法复杂度。
- 未来方向（论文声明）：将句法复杂度纳入课程难度度量是未来方向。