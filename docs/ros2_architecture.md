# ROS 2 架构与接口

## 节点图

```text
camera_node ──/camera/image_raw────────┬──> lane_node ──/perception/lane──────┐
                                      └──> yolo_node ──/perception/detections┤
decision_node <───────────────────────────────────────────────────────────────┘
decision_node ──/decision/action_command──> chassis_node ──/chassis/status
```

`chassis_node` 是唯一允许打开 ESP32 串口的 ROS 节点。相机流使用 depth=1、
best-effort QoS，控制和状态消息使用可靠队列。

## 消息契约

- `LaneResult`：有效标志、归一化转向值 `[-1,1]`、车道中心、置信度和推理耗时。
- `DetectionArray`：图像尺寸、推理耗时及七类 `Detection2D` 检测框。
- `ActionCommand`：高层动作、目标 RPM、转向、持续时间、来源和急停标志。
- `ChassisStatus`：串口连接、ESP32 ACK、四轮目标和错误信息。

决策节点以 20 Hz 运行。收到 `person` 或 `obstacle` 会立即抢占正在执行的离散动作；
车道消息超过 0.3 秒、检测消息超过 0.5 秒即视为过期。检测过期不会阻止巡线，但车道
过期必定停车。

## 启动入口

```bash
ros2 launch smartcar_bringup perception.launch.py
ros2 launch smartcar_bringup lane_follow.launch.py dry_run:=true
ros2 launch smartcar_bringup car.launch.py dry_run:=true
ros2 launch smartcar_bringup replay.launch.py images:=/path/to/images
```

运行 ONNX 后端时必须同时覆盖两个模型路径：

```bash
ros2 launch smartcar_bringup car.launch.py \
  backend:=onnx dry_run:=true \
  lane_model:=$SMARTCAR_MODEL_ROOT/lane/lanenet_hnet_finetune_unified_best.onnx \
  yolo_model:=$SMARTCAR_MODEL_ROOT/landmark/yolov5_incremental_v3_best.onnx
```

