# 故障排查

- 相机打不开：检查 `/dev/video*`、用户权限、MJPG/分辨率支持，先跑 `camera-test`。
- ONNX 失败：检查模型校验和、输入 shape、NumPy/ONNX Runtime 版本和输出列数。
- OM 失败：确认芯片为 310B1、CANN/ATC 版本兼容且已加载环境。
- ROS 无图像：检查 `/camera/image_raw` 频率、QoS 和 `cv_bridge`。
- 一启动就停车：查看 lane 有效性、时间戳超时、person/obstacle 检测及串口状态。
- ESP32 无 ACK：确认端口、权限、115200 baud、14 字节小端协议与 `-12345` 校验。
- 车辆方向相反：先验证 `motor_signs`，再验证固件 `ENCODER_SIGN`，不要用 PID 掩盖接线错误。
- 速度随电量变化：记录目标/实际 RPM，重新标定每圈计数、前馈与 PID；不要改回开环 PWM。

每次排障记录复现命令、配置副本、设备环境、日志摘要和修复 Commit ID；不要把包含真实凭据或个人信息的日志提交到公开仓库。无法在板端复现的问题标记“待现场验证”，交接时同步写入 [交接记录](handover.md)。

