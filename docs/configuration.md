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

