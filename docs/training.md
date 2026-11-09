# 模型训练与导出

数据集不随本仓库交付。LaneNet 数据需包含图像、binary mask、instance mask 和
`splits.csv`；YOLO 数据需按 `images/{train,val,test}` 与 `labels/...` 组织。

```bash
python3 -m pip install -r requirements/training.txt
python3 training/lane/train.py --config training/configs/lanenet.yaml
python3 training/lane/export_onnx.py --checkpoint /path/best.pth --output /path/model.onnx
python3 training/landmark/train_smartcar.py --config training/configs/yolov5.yaml
```

YOLOv5 上游源码放在 `external/yolov5`，必须遵守 GPL-3.0。导出 ONNX 后，在与目标板
CANN 兼容的环境中执行：

```bash
bash training/atc_convert.sh model.onnx output_prefix 'input:1,3,256,512' Ascend310B1
```

YOLO 的实际输入名和形状应以 ONNX 检查结果为准。每次替换模型都要同步更新
`models/SHA256SUMS`、类别顺序、预处理参数，并分别跑 ONNX 和 OM smoke test。

