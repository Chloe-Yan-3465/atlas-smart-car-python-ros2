from __future__ import annotations

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from smartcar_interfaces.msg import LaneResult as LaneResultMsg

from smartcar_core.inference import create_backend
from smartcar_core.perception.lane import LaneDetector
from .common import IMAGE_QOS


class LaneNode(Node):
    def __init__(self):
        super().__init__("lane_node")
        for name, default in (("backend", "om"), ("model_path", ""), ("width", 512), ("height", 256), ("min_pixels", 80), ("device_id", 0)):
            self.declare_parameter(name, default)
        backend = create_backend(str(self.get_parameter("backend").value), str(self.get_parameter("model_path").value), int(self.get_parameter("device_id").value))
        self.detector = LaneDetector(backend, int(self.get_parameter("width").value), int(self.get_parameter("height").value), int(self.get_parameter("min_pixels").value))
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(LaneResultMsg, "/perception/lane", 10)
        self.subscription = self.create_subscription(Image, "/camera/image_raw", self.on_image, IMAGE_QOS)

    def on_image(self, message):
        try:
            result = self.detector.detect(self.bridge.imgmsg_to_cv2(message, "bgr8"))
            out = LaneResultMsg(header=message.header, valid=result.valid, steering=result.steering, center_x=result.center_x, confidence=result.confidence, inference_ms=result.inference_ms)
            self.publisher.publish(out)
        except Exception as exc:
            self.get_logger().error(f"Lane inference failed: {exc}")

    def destroy_node(self):
        self.detector.backend.close(); return super().destroy_node()


def main(args=None):
    rclpy.init(args=args); node = LaneNode()
    try: rclpy.spin(node)
    finally: node.destroy_node(); rclpy.shutdown()

