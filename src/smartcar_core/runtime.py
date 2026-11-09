from __future__ import annotations

import logging
from time import monotonic

from .camera import CameraSource
from .chassis import SerialController
from .config import project_path
from .decision import DecisionEngine
from .inference import create_backend
from .perception import LaneDetector, YoloDetector

LOG = logging.getLogger(__name__)


class SmartCarRuntime:
    def __init__(self, config: dict, dry_run: bool = False, source: str | int | None = None, serial_port: str | None = None):
        self.config = config
        root = config["_project_root"]
        camera_cfg, model_cfg, chassis_cfg = config["camera"], config["models"], config["chassis"]
        self.camera = CameraSource(source if source is not None else camera_cfg["source"], camera_cfg["width"], camera_cfg["height"], camera_cfg["fps"], loop=True)
        backend = model_cfg["backend"]
        lane_path = project_path(model_cfg["lane"][f"{backend}_path"], root)
        yolo_path = project_path(model_cfg["yolo"][f"{backend}_path"], root)
        self.lane_backend = create_backend(backend, lane_path, model_cfg.get("device_id", 0))
        self.yolo_backend = create_backend(backend, yolo_path, model_cfg.get("device_id", 0))
        self.lane = LaneDetector(self.lane_backend, model_cfg["lane"]["width"], model_cfg["lane"]["height"], model_cfg["lane"]["min_pixels"])
        self.yolo = YoloDetector(self.yolo_backend, model_cfg["yolo"]["size"], model_cfg["yolo"]["confidence"], model_cfg["yolo"]["iou"])
        self.decision = DecisionEngine(config)
        self.controller = SerialController(serial_port or chassis_cfg["port"], chassis_cfg["baudrate"], chassis_cfg["timeout_s"], dry_run, tuple(chassis_cfg["motor_signs"]))

    def run(self, max_frames: int = 0) -> None:
        frame_count = 0
        try:
            while max_frames <= 0 or frame_count < max_frames:
                ok, frame = self.camera.read()
                if not ok:
                    self.controller.stop()
                    raise RuntimeError("Camera stream ended or failed")
                try:
                    lane = self.lane.detect(frame)
                    detections = self.yolo.detect(frame)
                    command = self.decision.decide(lane, detections, monotonic())
                    status = self.controller.execute(command)
                    if not status.connected:
                        raise RuntimeError(status.error)
                    LOG.info("frame=%d lane=%s steering=%.3f detections=%s action=%s ack=%s", frame_count, lane.valid, lane.steering, [d.class_name for d in detections], command.name, status.acknowledgement)
                except Exception:
                    self.controller.stop()
                    raise
                frame_count += 1
        finally:
            self.close()

    def close(self):
        self.controller.close()
        self.camera.close()
        self.lane_backend.close()
        self.yolo_backend.close()

