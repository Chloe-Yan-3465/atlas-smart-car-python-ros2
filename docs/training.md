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

## 数据与资产来源记录

- LaneNet/H-Net 输入为 RGB 512×256、数值范围 `[-1,1]`；运行侧使用二值车道输出计算下半幅中心与转向。训练数据路径样例在 `training/configs/lanenet.yaml`，须改成实际可访问的外部路径。
- YOLOv5 输入为 RGB 640×640、数值范围 `[0,1]`，使用 letterbox；类别顺序固定为 `left, right, turnaround, park, person, obstacle, crosswalk`。训练数据路径样例在 `training/configs/yolov5.yaml`。
- 六个归档权重来自课程第 3 组资料；训练数据来源和模型再分发授权尚未独立核实。新训练模型应记录数据版本、训练配置、权重、导出命令、CANN/ATC 版本和校验值，再由项目组确认发布权限。
- 完整数据集不在仓库中，目前无 NAS 稳定链接。正式内部交接需在 [交接记录](handover.md)补充 NAS 位置、获取方法及授权范围。模型清单和校验命令见 [模型说明](../models/README.md)。

