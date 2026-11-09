from __future__ import annotations

from rclpy.qos import HistoryPolicy, QoSProfile, ReliabilityPolicy

IMAGE_QOS = QoSProfile(
    depth=1,
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
)


def stamp_to_seconds(stamp) -> float:
    return float(stamp.sec) + float(stamp.nanosec) / 1e9

