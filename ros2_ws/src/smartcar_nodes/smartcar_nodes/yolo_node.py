from __future__ import annotations

import rclpy
from cv_bridge import CvBridge
from rclpy.node import Node
from sensor_msgs.msg import Image
from smartcar_interfaces.msg import Detection2D, DetectionArray

from smartcar_core.inference import create_backend
from smartcar_core.perception.yolo import YoloDetector
from .common import IMAGE_QOS


class YoloNode(Node):
    def __init__(self):
        super().__init__("yolo_node")
        for name, default in (("backend", "om"), ("model_path", ""), ("size", 640), ("confidence", 0.35), ("iou", 0.45), ("device_id", 0)):
            self.declare_parameter(name, default)
        backend = create_backend(str(self.get_parameter("backend").value), str(self.get_parameter("model_path").value), int(self.get_parameter("device_id").value))
        self.detector = YoloDetector(backend, int(self.get_parameter("size").value), float(self.get_parameter("confidence").value), float(self.get_parameter("iou").value))
        self.bridge = CvBridge()
        self.publisher = self.create_publisher(DetectionArray, "/perception/detections", 10)
        self.subscription = self.create_subscription(Image, "/camera/image_raw", self.on_image, IMAGE_QOS)

    def on_image(self, message):
        try:
            frame = self.bridge.imgmsg_to_cv2(message, "bgr8")
            detections = self.detector.detect(frame)
            out = DetectionArray(header=message.header, image_width=frame.shape[1], image_height=frame.shape[0], inference_ms=self.detector.last_inference_ms)
            out.detections = [Detection2D(class_id=d.class_id, class_name=d.class_name, confidence=d.confidence, x1=d.x1, y1=d.y1, x2=d.x2, y2=d.y2) for d in detections]
            self.publisher.publish(out)
        except Exception as exc:
            self.get_logger().error(f"YOLO inference failed: {exc}")

    def destroy_node(self):
        self.detector.backend.close(); return super().destroy_node()


def main(args=None):
    rclpy.init(args=args); node = YoloNode()
    try: rclpy.spin(node)
    finally: node.destroy_node(); rclpy.shutdown()

