from __future__ import annotations

import struct
from typing import Iterable

CHECK_VALUE = -12345
PACKET_STRUCT = struct.Struct("<7h")


def encode_packet(wheels: Iterable[int], servos: Iterable[int] = (110, 90)) -> bytes:
    wheel_values = tuple(int(v) for v in wheels)
    servo_values = tuple(int(v) for v in servos)
    if len(wheel_values) != 4 or len(servo_values) != 2:
        raise ValueError("A packet requires four wheel RPM values and two servo angles")
    if any(not -300 <= value <= 300 for value in wheel_values):
        raise ValueError("Wheel target is outside the firmware range -300..300 RPM")
    if any(not 0 <= value <= 180 for value in servo_values):
        raise ValueError("Servo angle is outside 0..180 degrees")
    return PACKET_STRUCT.pack(*wheel_values, *servo_values, CHECK_VALUE)


def decode_packet(packet: bytes) -> tuple[int, int, int, int, int, int]:
    if len(packet) != PACKET_STRUCT.size:
        raise ValueError(f"Expected {PACKET_STRUCT.size} bytes, got {len(packet)}")
    values = PACKET_STRUCT.unpack(packet)
    if values[-1] != CHECK_VALUE:
        raise ValueError("Invalid packet check value")
    return values[:-1]

