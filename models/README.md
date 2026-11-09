# 模型归档

模型仅在本目录保存一份，供纯 Python 与 ROS 2 共同引用。

| 类型 | 训练权重 | CPU 验证 | Atlas 实车 |
|---|---|---|---|
| 车道线 | `lane/*.pth` | `lane/*.onnx` | `lane/*_310b1.om` |
| 七类地标 | `landmark/*.pt` | `landmark/*.onnx` | `landmark/*_310b1.om` |

提交 Git 时建议使用 Git LFS。`SHA256SUMS` 用于确认复制和部署完整性。

