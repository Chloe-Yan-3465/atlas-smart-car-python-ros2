# Atlas、CANN 与 ROS 2 部署

基线为 Ubuntu 22.04、ROS 2 Humble、与设备匹配的 CANN/ais-bench。先确认
`npu-smi info` 显示 310B1，再加载 CANN 环境：

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /opt/ros/humble/setup.bash
bash scripts/build_atlas.sh
sha256sum -c models/SHA256SUMS
```

模型文件在 `models/`，运行 ROS 2 前设置：

```bash
export SMARTCAR_MODEL_ROOT=/opt/smart_car/models
source ros2_ws/install/setup.bash
ros2 launch smartcar_bringup perception.launch.py
ros2 topic hz /perception/lane
ros2 topic echo /perception/detections
ros2 launch smartcar_bringup car.launch.py dry_run:=true
```

CPU/ONNX ROS 联调需同时传入 `backend:=onnx`、`lane_model:=...onnx`、
`yolo_model:=...onnx`。`acl`、`ais_bench`、`rclpy` 和 `cv_bridge` 不写入 pip
requirements，分别由 CANN 和 ROS 安装提供。

