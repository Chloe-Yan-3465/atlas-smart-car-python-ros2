#!/usr/bin/env python3
"""Run both archived ONNX models on a generated frame and validate output contracts."""
from pathlib import Path

import numpy as np
from smartcar_core.inference import OnnxBackend
from smartcar_core.perception.lane import LaneDetector
from smartcar_core.perception.yolo import YoloDetector

ROOT = Path(__file__).resolve().parents[1]


def main():
    frame = np.zeros((720, 1280, 3), np.uint8)
    lane_backend = OnnxBackend(ROOT / "models/lane/lanenet_hnet_finetune_unified_best.onnx")
    yolo_backend = OnnxBackend(ROOT / "models/landmark/yolov5_incremental_v3_best.onnx")
    try:
        lane = LaneDetector(lane_backend).detect(frame)
        detections = YoloDetector(yolo_backend).detect(frame)
        print(f"lane_ok valid={lane.valid} inference_ms={lane.inference_ms:.2f}")
        print(f"yolo_ok detections={len(detections)}")
    finally:
        lane_backend.close(); yolo_backend.close()


if __name__ == "__main__": main()

