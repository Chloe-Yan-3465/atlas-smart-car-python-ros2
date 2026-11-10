# LaneNet/H-Net

外部数据结构：`images/`、`binary_masks/`、`instance_masks/`、`splits.csv`。修改
`training/configs/lanenet.yaml` 后运行：

```bash
python training/lane/train.py --config training/configs/lanenet.yaml
python training/lane/training_status.py
python training/lane/export_onnx.py \
  --checkpoint models/lane/runs/best.pth \
  --output models/lane/lanenet.onnx
python training/lane/infer_onnx.py --model models/lane/lanenet.onnx --images /path/to/val
```

网络同时输出二值车道分割、实例 embedding 与 H-Net 参数。实车共享后处理默认使用二值
输出计算下半幅车道中心，输入为 RGB 512×256、归一化到 `[-1,1]`。

数据集不随仓库交付，样例路径需在 `training/configs/lanenet.yaml` 中替换。
训练输出目录默认 `models/lane/runs`，属于运行产物；最终归档模型、校验值
和授权待核实项见 [模型说明](../../models/README.md)与
[交接记录](../../docs/handover.md)。运行命令须从仓库根目录执行。

