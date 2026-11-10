# ROS 2 架构与接口

稳定代码基线和运行状态见 [根 README](../README.md)。本架构由 `smartcar_interfaces`、`smartcar_nodes`、`smartcar_bringup` 三个 ROS 2 Humble 包组成；底层感知和决策复用 `smartcar_core`。

## 节点与 Topic

| 发布节点 | Topic | 消息类型 | 订阅节点 | 作用 |
|---|---|---|---|---|
| `camera_node` | `/camera/image_raw` | `sensor_msgs/msg/Image` | `lane_node`、`yolo_node` | BGR 图像，由 `cv_bridge` 转换 |
| `lane_node` | `/perception/lane` | `smartcar_interfaces/msg/LaneResult` | `decision_node` | 车道有效性、转向与置信度 |
| `yolo_node` | `/perception/detections` | `smartcar_interfaces/msg/DetectionArray` | `decision_node` | 七类检测框 |
| `decision_node` | `/decision/action_command` | `smartcar_interfaces/msg/ActionCommand` | `chassis_node` | 高层动作、速度与急停标志 |
| `chassis_node` | `/chassis/status` | `smartcar_interfaces/msg/ChassisStatus` | 外部监控终端 | 串口状态、ACK、目标轮速与错误 |

`chassis_node` 是唯一打开 ESP32 串口的节点。`/camera/image_raw` 使用 depth=1、best-effort QoS，`lane_node` 与 `yolo_node` 使用同一图像 QoS 订阅；其余 Topic 使用可靠队列 depth=10。QoS 不匹配时可能看不到图像。

## 消息字段与决策时效

| 消息 | 关键字段 |
|---|---|
| `LaneResult` | `header`、`valid`、`steering`、`center_x`、`confidence`、`inference_ms` |
| `Detection2D` | `class_id`、`class_name`、`confidence`、`x1/y1/x2/y2` |
| `DetectionArray` | `header`、图像宽高、`inference_ms`、`detections[]` |
| `ActionCommand` | `header`、`name`、`speed_rpm`、`steering`、`duration_s`、`source`、`emergency` |
| `ChassisStatus` | `header`、`connected`、`acknowledgement`、`wheel_targets[4]`、`error` |

决策节点默认 20 Hz。人员或障碍检测优先触发急停；离散地标动作执行期间可被急停抢占。车道结果超过 0.3 秒视为过期并停车；检测结果超过 0.5 秒时被忽略，车道仍可继续参与巡线。参数均可按实际场地标定，见 [配置参考](configuration.md)。

本项目**未定义 Service 或 ROS Action**；“动作”指 `ActionCommand` Topic 中的业务动作。串口协议见 [固件说明](../firmware/esp32_pid/README.md)。

## 参数与启动入口

| 参数组 | 主要参数 | 来源 |
|---|---|---|
| 相机 | `source`、`width`、`height`、`fps` | `smartcar_bringup/config/car_params.yaml`；部分由 launch 覆盖 |
| 感知 | `backend`、`model_path`、`device_id`、输入尺寸、阈值 | 同上及 launch 的模型参数 |
| 决策 | `control_hz`、感知超时、置信度、RPM、动作时长/冷却 | 参数 YAML |
| 底盘 | `port`、`baudrate`、`timeout_s`、`motor_signs`、`dry_run` | 参数 YAML；`dry_run` 可由 launch 覆盖 |

| launch 文件 | 包含节点 | 用途 |
|---|---|---|
| `car.launch.py` | 五个节点 | 整车；默认 OM 和 `dry_run:=true` |
| `perception.launch.py` | 相机、车道、地标 | 仅感知 |
| `lane_follow.launch.py` | 相机、车道、决策、底盘 | 仅巡线 |
| `replay.launch.py` | 包含整车 launch | 目录图片循环回放，强制 `dry_run` |

安装、构建、ONNX 模型路径覆盖命令与 Topic 验证见 [ROS 2 工作空间说明](../ros2_ws/README.md)。注意：`perception.launch.py` 和 `lane_follow.launch.py` 的模型路径按 OM 文件设置；普通电脑的完整 ONNX 联调使用可同时传入 `lane_model`、`yolo_model` 的 `car.launch.py`。
