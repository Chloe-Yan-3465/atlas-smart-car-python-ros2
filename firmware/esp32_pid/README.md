# ESP32 四轮编码器 PID 固件

接线采用第 19 组方案，全部可调参数集中在 `config.h`。Arduino IDE 打开
`car_ctrl_esp32.ino`，开发板选择 ESP32 Dev Module。

也可使用 PlatformIO：`platformio run -d firmware/esp32_pid`。

| 轮 | 电机 GPIO | 编码器 A/B |
|---|---|---|
| M1 | 12/13 | 25/26 |
| M2 | 14/15 | 32/33 |
| M3 | 16/17 | 34/35 |
| M4 | 18/19 | 36/39 |

舵机使用 GPIO21/22。GPIO34/35/36/39 无内部上拉，开漏编码器必须外接
4.7k~10k 上拉。首次运行必须架空车轮，依次设置
`PID_SELF_TEST_MODE=true` 和 `SELF_TEST_MOTOR_INDEX=0..3`，确认正目标得到正 RPM。

协议为 115200 baud、7 个小端 `int16`：
`[M1 RPM, M2 RPM, M3 RPM, M4 RPM, servo1, servo2, -12345]`。
有效、无效、方向故障、障碍分别回复 `SUCC/BAD/FAULT/FAIL`。连续 2 秒未收到
有效包会停车并回复 `TIMEOUT`。PID、每圈计数和方向符号必须按实车重新标定。

接手前应从 [根 README](../../README.md)核对稳定代码基线与环境要求，再按
[硬件接线](../../docs/hardware.md)、[PID 标定](../../docs/pid_calibration.md)和
[验收清单](../../docs/acceptance.md)记录逐轮方向、脉冲数、目标/实测 RPM、
失联停车及最终参数。当前默认参数来自第 19 组接线参考，尚无本车实测标定记录；
首次通电须架空车轮并准备物理断电。固件烧录与 PID 效果仍待实车验证。

