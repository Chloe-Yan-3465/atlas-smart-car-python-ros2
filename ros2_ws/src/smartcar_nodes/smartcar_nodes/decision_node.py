from __future__ import annotations

from time import monotonic

import rclpy
from rclpy.node import Node
from smartcar_interfaces.msg import ActionCommand as ActionCommandMsg
from smartcar_interfaces.msg import DetectionArray, LaneResult as LaneResultMsg

from smartcar_core.decision import DecisionEngine
from smartcar_core.types import Detection, LaneResult


class DecisionNode(Node):
    def __init__(self):
        super().__init__("decision_node")
        defaults = {
            "control_hz": 20.0, "lane_timeout_s": 0.30, "detection_timeout_s": 0.50,
            "detection_confidence": 0.35, "action_cooldown_s": 2.0,
            "normal_rpm": 80.0, "crawl_rpm": 35.0, "turn_rpm": 70.0,
            "turn_left_duration_s": 0.55, "turn_right_duration_s": 0.55,
            "turnaround_duration_s": 1.10, "park_duration_s": 1.20,
        }
        for name, value in defaults.items(): self.declare_parameter(name, value)
        self.config = {"decision": {
            "lane_timeout_s": self._p("lane_timeout_s"), "detection_timeout_s": self._p("detection_timeout_s"),
            "detection_confidence": self._p("detection_confidence"), "action_cooldown_s": self._p("action_cooldown_s"),
            "normal_rpm": self._p("normal_rpm"), "crawl_rpm": self._p("crawl_rpm"), "turn_rpm": self._p("turn_rpm"),
            "action_durations_s": {name: self._p(f"{name}_duration_s") for name in ("turn_left", "turn_right", "turnaround", "park")},
        }}
        self.engine = DecisionEngine(self.config)
        self.lane = None
        self.detections = []
        self.detections_at = -1e9
        self.publisher = self.create_publisher(ActionCommandMsg, "/decision/action_command", 10)
        self.create_subscription(LaneResultMsg, "/perception/lane", self.on_lane, 10)
        self.create_subscription(DetectionArray, "/perception/detections", self.on_detections, 10)
        self.timer = self.create_timer(1.0 / float(self._p("control_hz")), self.tick)

    def _p(self, name): return self.get_parameter(name).value

    def on_lane(self, msg):
        self.lane = LaneResult(msg.valid, msg.steering, msg.center_x, msg.confidence, monotonic(), msg.inference_ms)

    def on_detections(self, msg):
        self.detections = [Detection(d.class_id, d.class_name, d.confidence, d.x1, d.y1, d.x2, d.y2) for d in msg.detections]
        self.detections_at = monotonic()

    def tick(self):
        now = monotonic()
        detections = self.detections if now - self.detections_at <= float(self.config["decision"]["detection_timeout_s"]) else []
        action = self.engine.decide(self.lane, detections, now)
        msg = ActionCommandMsg()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name, msg.speed_rpm, msg.steering = action.name, action.speed_rpm, action.steering
        msg.duration_s, msg.source, msg.emergency = action.duration_s, action.source, action.emergency
        self.publisher.publish(msg)


def main(args=None):
    rclpy.init(args=args); node = DecisionNode()
    try: rclpy.spin(node)
    finally: node.destroy_node(); rclpy.shutdown()

