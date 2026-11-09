from __future__ import annotations

from time import monotonic
from typing import Sequence

from .types import ActionCommand, Detection, LaneResult


class DecisionEngine:
    """Deterministic safety-first policy shared by native Python and ROS 2."""

    DISCRETE = {"left": "turn_left", "right": "turn_right", "turnaround": "turnaround", "park": "park"}

    def __init__(self, config: dict):
        self.cfg = config
        self.last_action_at: dict[str, float] = {}
        self.active_action: ActionCommand | None = None
        self.active_until = -1e9

    def decide(
        self,
        lane: LaneResult | None,
        detections: Sequence[Detection],
        now: float | None = None,
    ) -> ActionCommand:
        now = monotonic() if now is None else now
        decision = self.cfg["decision"]
        min_conf = float(decision["detection_confidence"])
        current = [d for d in detections if d.confidence >= min_conf]

        if any(d.class_name in {"person", "obstacle"} for d in current):
            self.active_action = None
            return ActionCommand("stop", source="emergency_detection", emergency=True, timestamp=now)

        if self.active_action is not None and now < self.active_until:
            return self.active_action
        self.active_action = None

        discrete = sorted((d for d in current if d.class_name in self.DISCRETE), key=lambda d: d.confidence, reverse=True)
        if discrete:
            detected = discrete[0]
            cooldown = float(decision["action_cooldown_s"])
            if now - self.last_action_at.get(detected.class_name, -1e9) >= cooldown:
                self.last_action_at[detected.class_name] = now
                name = self.DISCRETE[detected.class_name]
                self.active_action = ActionCommand(
                    name,
                    float(decision["turn_rpm"]),
                    duration_s=float(decision["action_durations_s"].get(name, 0.8)),
                    source=f"landmark:{detected.class_name}",
                    timestamp=now,
                )
                self.active_until = now + self.active_action.duration_s
                return self.active_action

        crosswalk = any(d.class_name == "crosswalk" for d in current)
        if lane is None or now - lane.timestamp > float(decision["lane_timeout_s"]):
            return ActionCommand("stop", source="lane_timeout", emergency=True, timestamp=now)
        if not lane.valid:
            return ActionCommand("stop", source="lane_lost", timestamp=now)

        speed = float(decision["crawl_rpm"] if crosswalk else decision["normal_rpm"])
        return ActionCommand("follow_lane", speed, lane.steering, source="crosswalk" if crosswalk else "lane", timestamp=now)

