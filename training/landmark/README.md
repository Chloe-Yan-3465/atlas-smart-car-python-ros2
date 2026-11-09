# 七类 YOLOv5 地标检测

类别顺序固定为 `left, right, turnaround, park, person, obstacle, crosswalk`。

```bash
bash training/landmark/fetch_yolov5.sh
python training/landmark/train_smartcar.py --config training/configs/yolov5.yaml
python training/landmark/training_status.py
bash training/landmark/export_onnx.sh
bash training/atc_convert.sh models/landmark/yolov5.onnx \
  models/landmark/yolov5_310b1 'images:1,3,640,640' Ascend310B1
```

训练脚本会检查三份 split 的图片/标签对应关系、类别编号和归一化坐标。YOLOv5 上游源码
使用 GPL-3.0，许可证副本位于 `training/YOLOV5_GPL-3.0_LICENSE`。

