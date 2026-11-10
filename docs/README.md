# 文档索引

从仓库根目录的 [README](../README.md) 开始，按“克隆—安装—配置—启动—验证”完成最小复现。本文档目录保留详细设计和现场记录入口。

| 任务 | 文档 |
|---|---|
| 在普通电脑运行纯 Python | [纯 Python 入口](../apps/pure_python/README.md)、[配置参考](configuration.md) |
| 在 Atlas 上安装 CANN/ROS 2 | [Atlas 部署](atlas_deployment.md)、[ROS 2 工作空间](../ros2_ws/README.md) |
| 了解 Topic、消息和参数 | [ROS 2 架构与接口](ros2_architecture.md) |
| 接线与底盘标定 | [硬件与接线](hardware.md)、[ESP32 固件](../firmware/esp32_pid/README.md)、[PID 标定](pid_calibration.md) |
| 模型获取、训练与导出 | [模型归档](../models/README.md)、[训练与导出](training.md)、[训练目录](../training/README.md) |
| 测试和排障 | [验收清单](acceptance.md)、[故障排查](troubleshooting.md) |
| 内部交接 | [交接记录与规范差距](handover.md) |

文档内容对应稳定代码基线 `344ed1d58b3ea1c207e7df9d28939200e779ef9d`，后续文档修订记录在 Git 历史中。现场验收项目需要维护人按实际结果填写，不能从 CPU 测试推定板端通过。
