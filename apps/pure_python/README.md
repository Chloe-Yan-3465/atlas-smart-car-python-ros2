# 纯 Python 入口

本入口直接使用 [共享核心](../../src/smartcar_core/) 运行车道感知、七类地标检测、决策与底盘控制，不需要 ROS 2。目标环境是 Ubuntu 22.04、Python ≥ 3.10；普通电脑使用 ONNX Runtime，Atlas 板端可按配置切换 OM。稳定代码基线及项目状态见 [根 README](../../README.md)。

## 安装与配置

从仓库根目录执行，首次克隆和模型校验步骤见 [根 README](../../README.md#4-安装配置运行与停止)：

```bash
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e '.[cpu]'
cp config/car.yaml config/local.yaml
```

编辑 `config/local.yaml` 的 `camera.source`、`models.backend`、模型路径与 `chassis.port`。相对模型路径以仓库根目录解析。默认后端为 `onnx`，默认串口为 `/dev/ttyUSB0`；本地配置文件已被 Git 忽略。配置字段见 [配置参考](../../docs/configuration.md)。

## 逐项验证与运行

```bash
smartcar --config config/local.yaml camera-test --source /dev/video0 --frames 30
smartcar --config config/local.yaml model-test --image /path/to/image.jpg
smartcar --config config/local.yaml run --dry-run --source /path/to/images --max-frames 30
```

`camera-test` 预期输出读取帧数和最后一帧形状；`model-test` 输出车道与检测结果；`run --dry-run` 将每帧动作写入日志而不打开串口。图片目录按文件名顺序循环回放。按 `Ctrl+C` 停止持续运行。

底盘接线及架空测试通过后，才执行串口与人工低速测试：

```bash
smartcar --config config/local.yaml serial-test --serial-port /dev/ttyUSB0 --rpm 30
smartcar --config config/local.yaml manual --serial-port /dev/ttyUSB0
```

`manual` 中 `w/s/a/d/x` 分别为前进/后退/左转/右转/停车，`q` 退出。动作输出由 `smartcar_core.decision.DecisionEngine` 决定，通过 `SerialController` 写入 ESP32 14 字节协议；接口和安全规则见 [根 README](../../README.md#5-关键技术与接口)与 [验收清单](../../docs/acceptance.md)。

Atlas 使用 OM 时，在 `config/local.yaml` 中把 `models.backend` 改为 `om`，核对两条 `om_path`，并加载 CANN 环境。板端 OM 推理尚需现场验证。运行日志默认输出到终端；本入口不创建固定输出目录。
