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

## 首次部署与停止

在空白 Atlas 环境中，先按 [根 README](../README.md#4-安装配置运行与停止)克隆仓库、运行 `git lfs pull` 并校验模型，再执行本页命令。确认串口、相机和模型根目录与实际设备一致；默认 `/dev/video0`、`/dev/ttyUSB0` 和 `/opt/smart_car/models` 只是样例值。仓库位于其他位置时，显式设置 `SMARTCAR_MODEL_ROOT`。用 `Ctrl+C` 停止 launch；板端首次运行保持 `dry_run:=true`。

`scripts/build_atlas.sh` 包含 `rosdep install`、`colcon build`、`colcon test` 和结果检查。板端 OM 推理及实车 PID 尚无当前环境验证结果，按 [验收清单](acceptance.md)记录实际输出后再开放底盘。

