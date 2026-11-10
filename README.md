# Atlas 200I DK A2 智能小车：纯 Python 与 ROS 2

## 1. 项目简介与状态

本项目面向 Atlas 200I DK A2 智能小车，提供共用算法核心的两种运行方式：纯 Python 程序和 ROS 2 Humble 五节点系统。摄像头图像经 LaneNet/H-Net 车道模型和七类 YOLOv5 地标模型处理后，决策模块生成动作，由串口发送给 ESP32 四轮编码器 PID 底盘。支持图片目录回放和不连接底盘的 `dry_run` 验证。

| 项目 | 当前记录 |
|---|---|
| 完成状态 | 普通电脑可运行 ONNX 推理、单元测试和图片回放；Atlas OM、ROS 2 板端与实车 PID 尚待现场验收 |
| 稳定分支 | `main` |
| 稳定代码基线 Commit ID | `344ed1d58b3ea1c207e7df9d28939200e779ef9d` |
| Tag | 无 |
| 仓库 | <https://github.com/Chloe-Yan-3465/atlas-smart-car-python-ros2> |

该 Commit ID 定位已发布的代码基线。后续文档修订以 `main` 上的文档提交为准；新代码版本验收后须重新记录其完整 Commit ID 和测试结论。

主要功能：车道跟随、左转/右转/掉头/停车地标动作、人员与障碍急停、人行横道低速通过、丢线及感知超时停车。决策优先级为 **人员/障碍急停 → 离散地标动作 → 人行横道低速 → 车道跟随 → 丢线停车**。ESP32 连续两秒未收到有效串口包时独立停车。

## 2. 技术栈与环境

| 项目 | 要求 |
|---|---|
| 目标操作系统 | Ubuntu 22.04；开发电脑建议同版本 |
| 语言与运行时 | Python ≥ 3.10；ESP32 Arduino/PlatformIO C++ |
| Python 依赖 | 版本范围以 [`pyproject.toml`](pyproject.toml) 与 [`requirements/`](requirements/) 为准；CPU 推理使用 ONNX Runtime |
| ROS 2 | Humble；ROS 包依赖由各 `package.xml` 和 `rosdep` 管理 |
| 实车硬件 | Atlas 200I DK A2、Ascend 310B1、USB 摄像头、ESP32、四个 GMR 编码电机及两路舵机 |
| 板端驱动 | 与 310B1 匹配的 CANN/Ascend 环境；OM 推理依赖板端环境 |

接线与供电见 [硬件说明](docs/hardware.md)；CANN/ROS 2 安装见 [Atlas 部署](docs/atlas_deployment.md)。

## 3. 项目结构

```text
smart_car/
├─ apps/pure_python/          # 非 ROS 2 使用说明；命令入口为 smartcar
├─ src/smartcar_core/         # 摄像头、推理、感知、决策、串口共享核心
├─ config/car.yaml            # 纯 Python 配置样例
├─ ros2_ws/src/
│  ├─ smartcar_interfaces/    # 自定义消息
│  ├─ smartcar_nodes/         # camera/lane/yolo/decision/chassis 节点
│  └─ smartcar_bringup/       # launch 与 ROS 参数样例
├─ firmware/esp32_pid/       # ESP32 四编码电机 PID 固件
├─ training/                 # LaneNet/H-Net、YOLOv5 训练和导出
├─ models/                   # PTH/PT、ONNX、OM；六个文件由 Git LFS 管理
├─ requirements/             # runtime、cpu-test、training、dev 分组
├─ scripts/                  # Atlas 构建与板端 smoke test
├─ tools/                    # 工程检查与真实 ONNX smoke test
├─ tests/                    # 感知、决策、协议和伪串口测试
└─ docs/                     # 部署、接口、标定、排障与交接文档
```

运行日志默认输出到终端；仓库不预置运行结果。训练和构建的 `runs/`、`outputs/`、`build/`、`install/`、`log/` 不纳入版本控制。完整文档索引见 [`docs/README.md`](docs/README.md)。

## 4. 安装、配置、运行与停止

以下命令在 Ubuntu 22.04 终端执行。克隆时需要 Git LFS 获取真实模型文件。若需精确恢复已发布代码基线，在克隆后执行 `git checkout 344ed1d58b3ea1c207e7df9d28939200e779ef9d`，再执行 `git lfs pull`。

```bash
git lfs install
git clone https://github.com/Chloe-Yan-3465/atlas-smart-car-python-ros2.git
cd atlas-smart-car-python-ros2
git lfs pull
sha256sum -c models/SHA256SUMS
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[cpu,dev]'
python3 -m unittest discover -s tests -v
python3 tools/check_project.py
python3 tools/model_smoke.py
```

普通电脑使用 ONNX。将样例复制为本地配置，按设备修改 `camera.source`、模型路径和 `chassis.port`。图片目录需包含可读取的图像文件。

```bash
cp config/car.yaml config/local.yaml
smartcar --config config/local.yaml model-test
smartcar --config config/local.yaml run --dry-run --source /path/to/images --max-frames 30
```

`--config` 是全局选项，写在子命令之前。可用 `Ctrl+C` 停止运行，或用 `--max-frames` 自动退出。`--dry-run` 不打开底盘串口。真实相机、串口与固件的逐项测试见 [纯 Python 说明](apps/pure_python/README.md)、[配置参考](docs/configuration.md)和[验收清单](docs/acceptance.md)。

Atlas 端安装 CANN、ROS 2 Humble 和相机驱动后，从仓库根目录执行：

```bash
source /usr/local/Ascend/ascend-toolkit/set_env.sh
source /opt/ros/humble/setup.bash
bash scripts/build_atlas.sh
export SMARTCAR_MODEL_ROOT="$PWD/models"
source ros2_ws/install/setup.bash
ros2 launch smartcar_bringup car.launch.py dry_run:=true
```

另开终端并加载相同 ROS 环境，执行 `ros2 topic hz /camera/image_raw`、`ros2 topic echo /perception/lane` 和 `ros2 topic echo /decision/action_command` 验证。按 `Ctrl+C` 停止 launch。默认 `dry_run:=true`；低速实车运行前须完成 [板端及架空验收](docs/acceptance.md)。详细步骤见 [ROS 2 说明](ros2_ws/README.md)。

## 5. 关键技术与接口

| 模块/入口 | 输入 | 输出/用途 |
|---|---|---|
| `smartcar_core.camera.CameraSource.read()` | 摄像头设备或图片目录 | `(ok, BGR 图像)` |
| `smartcar_core.perception.LaneDetector.detect()` | BGR 图像、车道模型 | `LaneResult`：有效性、车道中心、归一化转向、置信度 |
| `smartcar_core.perception.YoloDetector.detect()` | BGR 图像、地标模型 | 七类 `Detection` 列表 |
| `smartcar_core.decision.DecisionEngine.decide()` | 车道结果、检测列表、时间 | `ActionCommand`；丢线/过期时停车 |
| `smartcar_core.chassis.SerialController.execute()` | `ActionCommand` | ESP32 串口包与 `ChassisStatus` |
| `smartcar` CLI | `run`、`manual`、`camera-test`、`model-test`、`serial-test` | 纯 Python 运行与逐项自检 |

ROS 2 主数据流：`/camera/image_raw` → `/perception/lane`、`/perception/detections` → `/decision/action_command` → `/chassis/status`。消息类型、节点、QoS、参数和 launch 文件见 [ROS 2 接口表](docs/ros2_architecture.md)。本工程未定义 ROS Service 或 ROS Action；动作命令由自定义 Topic 消息传输。

## 6. 数据、模型与第三方内容

完整训练数据集**不随仓库交付**；目前没有可填写的 NAS 稳定链接。重训时按 [训练文档](docs/training.md)准备外部数据，并修改 `training/configs/` 中的路径。不要提交个人路径、敏感数据或真实凭据。

六个课程资料模型位于 [`models/`](models/README.md)：车道 PTH/ONNX/310B1 OM 与地标 PT/ONNX/310B1 OM，各存一份，由 Git LFS 管理。执行 `git lfs pull` 后用 [`models/SHA256SUMS`](models/SHA256SUMS) 校验。模型来自课程第 3 组资料；更具体的训练数据来源和再分发授权尚未从原始资料中独立核实。若按梦工厂规范进行正式内部交接，**仍需由项目组上传大模型至获授权的 NAS，补充稳定链接和来源/许可记录**；GitHub LFS 不代替规范要求的 NAS 记录。

YOLOv5 上游代码不内嵌于本仓库；其 GPL-3.0 说明和许可证副本见 [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md)。本仓库自有代码许可证见 [`LICENSE`](LICENSE)。

## 7. 测试、已知问题与维护交接

- 最小 CPU 验证：单元测试、`tools/check_project.py`、两份真实 ONNX 的 `tools/model_smoke.py`；预期均以退出码 0 结束，判据见 [验收清单](docs/acceptance.md)。
- 已知限制：当前无 Atlas/ESP32 现场验证结果；OM、ROS 2 板端、编码器方向、PID 参数和实车安全动作须逐项验收。训练数据不在仓库中。
- 后续任务：补齐 NAS 模型资产及授权记录，完成板端和实车验收，记录最终 PID/阈值标定。IMU、雷达、建图、远程控制不属于本阶段。
- 当前维护者：严之含。公开仓库所有者账号为 `Chloe-Yan-3465`；内部 GitLab 项目路径暂无（本项目首次上传），接手人和交接日期待填写。
- 交接记录与独立复现表：[`docs/handover.md`](docs/handover.md)。故障处理见 [排障文档](docs/troubleshooting.md)。

实车首测必须架空车轮，逐轮确认电机与编码器方向，并准备物理断电手段。人员/障碍、丢线、感知超时、相机或串口异常应触发停车；现场验证结果由验收人记录。
