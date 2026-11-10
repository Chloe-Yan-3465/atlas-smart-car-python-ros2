# 配置参考

原生入口读取 `config/car.yaml`。相对模型路径以仓库根目录解析；本机差异可复制为
`config/local.yaml` 并用 `--config` 指定。

- `camera`：设备/图片目录、分辨率和帧率。
- `models.backend`：普通电脑用 `onnx`，Atlas 用 `om`。
- `models.lane`：512×256 输入、最少车道像素数及模型路径。
- `models.yolo`：640 输入、置信度、NMS IoU、七类顺序和模型路径。
- `decision`：感知超时、正常/爬行/转弯 RPM、动作冷却和持续时间。
- `chassis`：串口、超时、四轮安装方向和舵机中位。

ROS 2 默认参数在 `smartcar_bringup/config/car_params.yaml`，launch 参数用于覆盖模型根目录、
后端、摄像头和 `dry_run`。类别顺序不得与训练配置或模型输出交换。

## 本地配置操作

从仓库根目录执行 `cp config/car.yaml config/local.yaml`，编辑后使用
`smartcar --config config/local.yaml run --dry-run --source /path/to/images --max-frames 30`。
`--config` 位于子命令之前；`config/local.yaml` 已在 `.gitignore` 中，适合存放本机设备路径，但不得写入密码、Token 或个人敏感信息。相对模型路径以仓库根目录解析。

| 字段 | 默认值 | 首次部署需核对 |
|---|---|---|
| `camera.source` | `/dev/video0` | 相机设备名或图片目录 |
| `models.backend` | `onnx` | 普通电脑为 `onnx`，Atlas 为 `om` |
| `models.lane.*_path` / `models.yolo.*_path` | `models/` 下归档文件 | 已执行 `git lfs pull`，两条路径与后端匹配 |
| `decision.lane_timeout_s` / `detection_timeout_s` | 0.30 / 0.50 秒 | 相机帧率与模型推理耗时 |
| `chassis.port` | `/dev/ttyUSB0` | 实际串口设备；`dry_run` 阶段不打开 |
| `chassis.motor_signs` | `[-1,-1,1,1]` | 架空逐轮验证方向后再用于实车 |

ROS 参数样例位于 `ros2_ws/src/smartcar_bringup/config/car_params.yaml`，其字段用途与纯 Python YAML 对应，但层级按 ROS 2 节点组织。完整参数分组与启动参数见 [接口文档](ros2_architecture.md)。不要直接把纯 Python 配置文件传给 ROS 2 launch。

