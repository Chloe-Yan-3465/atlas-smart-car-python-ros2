from __future__ import annotations

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image

from smartcar_core.camera import CameraSource
from .common import IMAGE_QOS


class CameraNode(Node):
    def __init__(self):
        super().__init__("camera_node")
        self.declare_parameter("source", "/dev/video0")
        self.declare_parameter("width", 1280)
        self.declare_parameter("height", 720)
        self.declare_parameter("fps", 30)
        source = str(self.get_parameter("source").value)
        fps = int(self.get_parameter("fps").value)
        self.camera = CameraSource(source, int(self.get_parameter("width").value), int(self.get_parameter("height").value), fps, loop=True)
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(Image, "/camera/image_raw", IMAGE_QOS)
        self.timer = self.create_timer(1.0 / max(fps, 1), self.publish_frame)

    def publish_frame(self):
        ok, frame = self.camera.read()
        if not ok:
            self.get_logger().error("Camera read failed; no image published")
            return
        message = self.bridge.cv2_to_imgmsg(frame, encoding="bgr8")
        message.header.stamp = self.get_clock().now().to_msg()
        message.header.frame_id = "camera"
        self.publisher.publish(message)

    def destroy_node(self):
        self.camera.close()
        return super().destroy_node()


def main(args=None):
    rclpy.init(args=args); node = CameraNode()
    try: rclpy.spin(node)
    finally: node.destroy_node(); rclpy.shutdown()

