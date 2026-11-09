# Atlas 200I DK A2 智能小车

本仓库提供共享算法核心下的两套完整入口：原生 Python 与 ROS 2 Humble。两者使用同一套
LaneNet/H-Net 车道感知、七类 YOLOv5 地标感知、确定性决策、ESP32 串口协议、模型和
四轮编码器 PID 固件。

## 目录

```text
apps/pure_python/       非 ROS 2 使用说明
src/smartcar_core/      两套入口共享的感知、决策、底盘代码
ros2_ws/src/            interfaces、nodes、bringup 三个 ROS 2 包
firmware/esp32_pid/     第 19 组接线方案的 ESP32 PID 固件
training/               LaneNet/H-Net 与七类 YOLOv5 训练/导出
models/                 PTH/PT、ONNX、Ascend310B1 OM（仅一份）
config/car.yaml         原生 Python 统一配置
docs/                   部署、接线、标定、排障与验收文档
tests/                  核心单元测试和伪串口测试
```

## 快速开始

普通电脑安装与验证：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[cpu,dev]'
python3 -m unittest discover -s tests -v
python3 tools/check_project.py
python3 tools/model_smoke.py
smartcar run --dry-run --source /path/to/images --max-frames 30
```

Atlas 部署：

```bash
bash scripts/build_atlas.sh
export SMARTCAR_MODEL_ROOT=$PWD/models
source ros2_ws/install/setup.bash
ros2 launch smartcar_bringup car.launch.py dry_run:=true
```

确认相机、感知话题、动作和底盘方向全部正确后，才可使用 `dry_run:=false`。本项目的
OM、ROS 2 和实车 PID 尚需在实际 Atlas/ESP32 上完成最终验收，详见
[验收清单](docs/acceptance.md)。

## 安全规则

- PID 首测必须架空车轮，并逐轮确认方向和编码器符号。
- `person`/`obstacle`、丢线、感知超时、相机或串口异常均停车。
- ESP32 连续两秒没有有效串口包会独立停车。
- 始终准备物理断电手段；不要在人员、线缆或易损物附近首次测试。

本阶段不含完整数据集、IMU、雷达、建图、融合、网页监控或远程接管。

