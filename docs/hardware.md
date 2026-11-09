# 硬件与接线

目标平台为 Atlas 200I DK A2（Ascend 310B1）、USB 摄像头、ESP32 IOT&Robot
四电机板、四个 GMR 编码电机及两路舵机。ESP32 接线见
[`firmware/esp32_pid/README.md`](../firmware/esp32_pid/README.md)。

Atlas 通过 USB 串口连接 ESP32，默认 `/dev/ttyUSB0`、115200 baud。使用
`udevadm info` 确认实际设备，建议用 udev 规则建立稳定别名。电机电源与逻辑电源应满足
板卡规格并共地；ESP32 GPIO 只允许 3.3V。GPIO34/35/36/39 若接开漏编码器必须外加上拉。

摄像头默认 1280×720、30 FPS、MJPG。安装后用 `smartcar camera-test` 验证，再启动模型。

