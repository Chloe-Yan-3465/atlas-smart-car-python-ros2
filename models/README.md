# 模型资产与获取

车道与地标模型各保留训练权重、普通电脑 ONNX、Atlas 310B1 OM 三种格式，纯 Python 与 ROS 2 共用本目录；六个大文件由 Git LFS 跟踪。

| 用途 | 训练权重 | CPU 验证 | Atlas 部署 |
|---|---|---|---|
| LaneNet/H-Net 车道线 | `lane/lanenet_hnet_finetune_unified_best.pth` | `lane/lanenet_hnet_finetune_unified_best.onnx` | `lane/lanenet_hnet_finetune_unified_310b1.om` |
| YOLOv5 七类地标 | `landmark/yolov5_incremental_v3_best.pt` | `landmark/yolov5_incremental_v3_best.onnx` | `landmark/yolov5_incremental_v3_310b1.om` |

从仓库根目录执行 `git lfs pull` 和 `sha256sum -c models/SHA256SUMS`。CPU 推理可执行 `python3 tools/model_smoke.py`；OM 推理需在 Atlas 板端、匹配 CANN 环境下验证。输入尺寸、归一化和类别顺序见 [模型训练与导出](../docs/training.md)，运行路径在 `config/car.yaml` 或 ROS launch 参数中配置。

这些归档模型来自课程第 3 组资料。仓库未包含训练数据集；模型训练数据来源及再分发授权尚未独立核实。当前公开仓库可通过 Git LFS 获取权重，但**尚无梦工厂内部 NAS 稳定链接**。正式内部交接需上传至获授权的 NAS，并在 [交接记录](../docs/handover.md)补充链接、资产来源、许可、获取和放置方法。不要将 Git LFS 指针误认为完整模型文件。
