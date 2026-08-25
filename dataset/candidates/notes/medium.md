# 1. 研究目标
- 将实时目标检测架构 D-FINE 扩展为支持实例分割的框架，同时保持低延迟与可部署性。
- 构建一个可复现的多后端部署管线，覆盖检测与分割两个任务。

# 2. 核心方法
- 检测部分继承原始 D-FINE，核心为 FDR（细化分布）与 GO-LSD（自蒸馏）。
- 新增一个轻量级 mask head，并加入 mask BCE 与 dice loss 进行监督。

# 3. 主要创新点
- 轻量级 mask head 设计，不引入高分辨率 backbone 特征。
- 多后端可复现部署协议（ONNX / TensorRT / OpenVINO）。

# 4. 实验结果与分析
- 在 TACO 数据集上与 YOLO26 对比，D-FINE-seg 的精度优于 YOLO26，延迟也更具优势。

# 5. 存在不足与未来方向
- 当前 mask head 没有 COCO 预训练权重，未来可在 COCO 上预训练以改善边界精度。
