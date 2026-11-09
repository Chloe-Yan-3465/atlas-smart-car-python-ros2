# 训练与导出

- `lane/`：LaneNet/H-Net 训练、ONNX 导出与离线推理。
- `landmark/`：七类 YOLOv5 训练封装与 ONNX 导出。
- `atc_convert.sh`：ONNX 转 Ascend 310B1 OM。

本仓库不包含数据集。配置中的数据路径应指向外部目录，类别顺序固定为：
`left, right, turnaround, park, person, obstacle, crosswalk`。

