# 训练与模型导出

本目录包含 LaneNet/H-Net 训练源码、七类 YOLOv5 训练封装、配置样例及 ONNX→OM 转换脚本；不含训练数据集。稳定代码基线、模型归档和部署状态见 [根 README](../README.md)及 [模型目录](../models/README.md)。

| 目录/文件 | 作用 |
|---|---|
| `lane/` | 数据读取、网络、损失、训练、ONNX 导出和离线推理 |
| `landmark/` | YOLOv5 获取、数据检查、训练和 ONNX 导出封装 |
| `configs/` | 数据路径、输入、批量等训练参数样例 |
| `atc_convert.sh` | 在匹配 CANN 环境下将 ONNX 转为 Ascend 310B1 OM |

从仓库根目录安装 `python3 -m pip install -r requirements/training.txt`，按 [训练文档](../docs/training.md)准备外部数据并修改配置路径，再使用 [车道训练步骤](lane/README.md)或[地标训练步骤](landmark/README.md)。导出后按模型文件名记录训练配置、输入形状、类别顺序和 `models/SHA256SUMS`，分别进行 ONNX 与 OM 验证。训练输出默认不纳入 Git。

YOLOv5 上游源码按脚本单独获取，不在本仓库内嵌；许可证为 GPL-3.0，副本位于 [`YOLOV5_GPL-3.0_LICENSE`](YOLOV5_GPL-3.0_LICENSE)。课程归档模型的具体授权尚待项目组核实。
