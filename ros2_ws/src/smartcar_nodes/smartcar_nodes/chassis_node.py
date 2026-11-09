from __future__ import annotations

import rclpy
from rclpy.node import Node
from smartcar_interfaces.msg import ActionCommand as ActionCommandMsg
from smartcar_interfaces.msg import ChassisStatus as ChassisStatusMsg

from smartcar_core.chassis import SerialController
from smartcar_core.types import ActionCommand


class ChassisNode(Node):
    def __init__(self):
        super().__init__("chassis_node")
        for name, default in (("port", "/dev/ttyUSB0"), ("baudrate", 115200), ("timeout_s", 0.3), ("dry_run", True), ("motor_signs", [-1, -1, 1, 1])):
            self.declare_parameter(name, default)
        self.controller = SerialController(
            str(self.get_parameter("port").value), int(self.get_parameter("baudrate").value),
            float(self.get_parameter("timeout_s").value), bool(self.get_parameter("dry_run").value),
            tuple(int(v) for v in self.get_parameter("motor_signs").value),
        )
        self.publisher = self.create_publisher(ChassisStatusMsg, "/chassis/status", 10)
        self.subscription = self.create_subscription(ActionCommandMsg, "/decision/action_command", self.on_action, 10)

    def on_action(self, msg):
        command = ActionCommand(msg.name, msg.speed_rpm, msg.steering, msg.duration_s, msg.source, msg.emergency)
        status = self.controller.execute(command)
        out = ChassisStatusMsg()
        out.header.stamp = self.get_clock().now().to_msg()
        out.connected, out.acknowledgement = status.connected, status.acknowledgement
        out.wheel_targets, out.error = list(status.wheel_targets), status.error
        self.publisher.publish(out)
        if status.error: self.get_logger().error(status.error)

    def destroy_node(self):
        self.controller.close(); return super().destroy_node()


def main(args=None):
    rclpy.init(args=args); node = ChassisNode()
    try: rclpy.spin(node)
    finally: node.destroy_node(); rclpy.shutdown()

