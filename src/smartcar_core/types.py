from __future__ import annotations

from dataclasses import dataclass, field
from time import monotonic


@dataclass(slots=True)
class LaneResult:
    valid: bool
    steering: float = 0.0  # normalized: -1 left, +1 right
    center_x: float = 0.5
    confidence: float = 0.0
    timestamp: float = field(default_factory=monotonic)
    inference_ms: float = 0.0


@dataclass(slots=True)
class Detection:
    class_id: int
    class_name: str
    confidence: float
    x1: float
    y1: float
    x2: float
    y2: float

    @property
    def area(self) -> float:
        return max(0.0, self.x2 - self.x1) * max(0.0, self.y2 - self.y1)


@dataclass(slots=True)
class ActionCommand:
    name: str
    speed_rpm: float = 0.0
    steering: float = 0.0
    duration_s: float = 0.0
    source: str = "internal"
    emergency: bool = False
    timestamp: float = field(default_factory=monotonic)


@dataclass(slots=True)
class ChassisStatus:
    connected: bool = False
    acknowledgement: str = ""
    command: ActionCommand = field(default_factory=lambda: ActionCommand("stop"))
    wheel_targets: tuple[int, int, int, int] = (0, 0, 0, 0)
    error: str = ""
    timestamp: float = field(default_factory=monotonic)

