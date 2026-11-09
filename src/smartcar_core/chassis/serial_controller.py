from __future__ import annotations

import atexit
from time import monotonic, sleep
from typing import Callable

from ..types import ActionCommand, ChassisStatus
from .protocol import encode_packet


def command_to_wheels(command: ActionCommand, motor_signs: tuple[int, int, int, int] = (-1, -1, 1, 1)) -> tuple[int, int, int, int]:
    speed = max(0, min(300, int(round(abs(command.speed_rpm)))))
    if command.name in {"stop", "park_complete"}:
        logical = (0, 0, 0, 0)
    elif command.name == "follow_lane":
        steering = max(-1.0, min(1.0, command.steering))
        left = int(round(speed * (1.0 + min(0.0, steering))))
        right = int(round(speed * (1.0 - max(0.0, steering))))
        logical = (left, left, right, right)
    elif command.name == "turn_left":
        logical = (-speed, -speed, speed, speed)
    elif command.name == "turn_right":
        logical = (speed, speed, -speed, -speed)
    elif command.name == "turnaround":
        logical = (-speed, -speed, speed, speed)
    elif command.name == "park":
        logical = (speed, -speed, -speed, speed)
    elif command.name == "reverse":
        logical = (-speed, -speed, -speed, -speed)
    else:
        logical = (speed, speed, speed, speed)
    return tuple(int(value * sign) for value, sign in zip(logical, motor_signs))


class SerialController:
    def __init__(
        self,
        port: str,
        baudrate: int = 115200,
        timeout_s: float = 0.3,
        dry_run: bool = False,
        motor_signs: tuple[int, int, int, int] = (-1, -1, 1, 1),
        serial_factory: Callable | None = None,
    ):
        self.port, self.baudrate, self.timeout_s = port, baudrate, timeout_s
        self.dry_run, self.motor_signs = dry_run, motor_signs
        self._serial_factory = serial_factory
        self._serial = None
        self._closed = False
        atexit.register(self.close)

    def connect(self) -> None:
        if self.dry_run or self._serial is not None:
            return
        if self._serial_factory is None:
            import serial

            self._serial_factory = serial.Serial
        self._serial = self._serial_factory(self.port, self.baudrate, timeout=self.timeout_s, write_timeout=self.timeout_s)

    def execute(self, command: ActionCommand, servos: tuple[int, int] = (110, 90)) -> ChassisStatus:
        wheels = command_to_wheels(command, self.motor_signs)
        if self.dry_run:
            return ChassisStatus(True, "DRY_RUN", command, wheels)
        last_error = None
        for attempt in range(2):
            try:
                self.connect()
                self._serial.reset_input_buffer()
                self._serial.write(encode_packet(wheels, servos))
                self._serial.flush()
                ack = self._serial.readline().decode("ascii", errors="replace").strip()
                accepted = ack.startswith(("SUCC", "OK"))
                if not accepted:
                    raise RuntimeError(f"ESP32 rejected command: {ack or 'no acknowledgement'}")
                return ChassisStatus(True, ack, command, wheels)
            except Exception as exc:
                last_error = exc
                self._disconnect()
                if attempt == 0:
                    sleep(0.05)
        return ChassisStatus(False, "", command, wheels, str(last_error), monotonic())

    def stop(self) -> ChassisStatus:
        command = ActionCommand("stop", source="safety")
        if self.dry_run:
            return ChassisStatus(True, "DRY_RUN", command, (0, 0, 0, 0))
        try:
            self.connect()
            self._serial.write(encode_packet((0, 0, 0, 0)))
            self._serial.flush()
            ack = self._serial.readline().decode("ascii", errors="replace").strip()
            return ChassisStatus(bool(ack), ack, command, (0, 0, 0, 0))
        except Exception as exc:
            return ChassisStatus(False, error=str(exc))

    def _disconnect(self) -> None:
        if self._serial is not None:
            try:
                self._serial.close()
            finally:
                self._serial = None

    def close(self) -> None:
        if self._closed:
            return
        self._closed = True
        try:
            if self._serial is not None:
                self.stop()
        finally:
            self._disconnect()

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *_):
        self.close()

