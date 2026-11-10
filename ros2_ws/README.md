# ROS 2 Humble 工作空间

本工作空间将共享核心包装为五个 ROS 2 节点。稳定代码基线、硬件、模型与测试状态见 [根 README](../README.md)。目标环境：Ubuntu 22.04、ROS 2 Humble、Python ≥ 3.10；Atlas OM 模式还需匹配 Ascend 310B1 的 CANN。

## 包与接口

| 包 | 用途 |
|---|---|
| `smartcar_interfaces` | `LaneResult`、`Detection2D`、`DetectionArray`、`ActionCommand`、`ChassisStatus` 消息 |
| `smartcar_nodes` | `camera_node`、`lane_node`、`yolo_node`、`decision_node`、`chassis_node` |
| `smartcar_bringup` | 参数 YAML、`car`、`perception`、`lane_follow`、`replay` 启动文件 |

Topic、消息字段、QoS 与参数表见 [接口文档](../docs/ros2_architecture.md)。本工程未定义 ROS Service 或 Action；`chassis_node` 是唯一持有底盘串口的节点。

## 克隆、安装与构建

先按 [根 README](../README.md#4-安装配置运行与停止)完成克隆、Git LFS 和模型校验。在 Atlas 上从仓库根目录执行：

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /opt/ros/humble/setup.bash
python3 -m pip install -e .
cd ros2_ws
rosdep install --from-paths src --ignore-src -r -y
colcon build --symlink-install
colcon test --event-handlers console_direct+
colcon test-result --verbose
source install/setup.bash
export SMARTCAR_MODEL_ROOT="$(cd .. && pwd)/models"
ros2 launch smartcar_bringup car.launch.py dry_run:=true
```

也可在仓库根目录运行 `bash scripts/build_atlas.sh` 完成安装、`rosdep`、构建与测试。按 `Ctrl+C` 停止 launch。默认 `dry_run:=true`；在板端验收前不应打开真实底盘串口。

## 启动方式与最小验证

```bash
ros2 launch smartcar_bringup perception.launch.py
ros2 launch smartcar_bringup lane_follow.launch.py dry_run:=true
ros2 launch smartcar_bringup replay.launch.py images:=/path/to/images
```

仅感知启动文件运行相机、车道和地标节点；仅巡线启动文件运行相机、车道、决策与底盘节点；图片回放文件使用目录作循环图像源且强制 `dry_run`。整车入口为 `car.launch.py`。

另开终端并加载 ROS 环境，执行：

```bash
ros2 topic list
ros2 topic hz /camera/image_raw
ros2 topic echo /perception/lane
ros2 topic echo /perception/detections
ros2 topic echo /decision/action_command
ros2 topic echo /chassis/status
```

普通电脑上运行 ONNX ROS 联调时，`car.launch.py` 必须同时覆盖后端和两条模型路径：

```bash
export SMARTCAR_MODEL_ROOT="$PWD/models"
ros2 launch smartcar_bringup car.launch.py backend:=onnx dry_run:=true \
  lane_model:="$SMARTCAR_MODEL_ROOT/lane/lanenet_hnet_finetune_unified_best.onnx" \
  yolo_model:="$SMARTCAR_MODEL_ROOT/landmark/yolov5_incremental_v3_best.onnx"
```

上例须在仓库根目录执行，并在已构建、已加载 `ros2_ws/install/setup.bash` 的终端运行。其他启动文件的模型路径按 OM 文件设置；其可覆盖参数以实际 launch 定义为准。ROS 2 板端、OM 与实车运行仍待现场验收；见 [Atlas 部署](../docs/atlas_deployment.md)和[验收清单](../docs/acceptance.md)。
