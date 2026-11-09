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

