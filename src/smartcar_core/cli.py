from __future__ import annotations

import argparse
import logging
from pathlib import Path

import cv2
import numpy as np

from .camera import CameraSource
from .chassis import SerialController
from .config import load_config, project_path
from .inference import create_backend
from .perception import LaneDetector, YoloDetector
from .runtime import SmartCarRuntime
from .types import ActionCommand


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(prog="smartcar")
    root.add_argument("--config", type=Path)
    root.add_argument("--verbose", action="store_true")
    commands = root.add_subparsers(dest="command", required=True)
    run = commands.add_parser("run")
    run.add_argument("--source")
    run.add_argument("--serial-port")
    run.add_argument("--dry-run", action="store_true")
    run.add_argument("--max-frames", type=int, default=0)
    manual = commands.add_parser("manual")
    manual.add_argument("--serial-port")
    manual.add_argument("--dry-run", action="store_true")
    camera = commands.add_parser("camera-test")
    camera.add_argument("--source")
    camera.add_argument("--frames", type=int, default=30)
    model = commands.add_parser("model-test")
    model.add_argument("--image", type=Path)
    serial = commands.add_parser("serial-test")
    serial.add_argument("--serial-port")
    serial.add_argument("--dry-run", action="store_true")
    serial.add_argument("--rpm", type=int, default=30)
    return root


def _manual(config: dict, args) -> None:
    cfg = config["chassis"]
    keys = {"w": "forward", "s": "reverse", "a": "turn_left", "d": "turn_right", "x": "stop"}
    with SerialController(args.serial_port or cfg["port"], cfg["baudrate"], cfg["timeout_s"], args.dry_run, tuple(cfg["motor_signs"])) as controller:
        print("Commands: w forward, s reverse, a left, d right, x stop, q quit")
        while (key := input("> ").strip().lower()) != "q":
            if key in keys:
                print(controller.execute(ActionCommand(keys[key], config["decision"]["crawl_rpm"])))


def _camera_test(config: dict, args) -> None:
    cfg = config["camera"]
    camera = CameraSource(args.source or cfg["source"], cfg["width"], cfg["height"], cfg["fps"])
    try:
        for index in range(args.frames):
            ok, frame = camera.read()
            if not ok:
                raise RuntimeError(f"Camera failed at frame {index}")
        print(f"camera ok: {args.frames} frames, last shape={frame.shape}")
    finally:
        camera.close()


def _model_test(config: dict, args) -> None:
    models, root = config["models"], config["_project_root"]
    image = cv2.imread(str(args.image)) if args.image else np.zeros((720, 1280, 3), np.uint8)
    if image is None:
        raise FileNotFoundError(args.image)
    backend_name = models["backend"]
    lane_backend = create_backend(backend_name, project_path(models["lane"][f"{backend_name}_path"], root))
    yolo_backend = create_backend(backend_name, project_path(models["yolo"][f"{backend_name}_path"], root))
    try:
        lane = LaneDetector(lane_backend, models["lane"]["width"], models["lane"]["height"]).detect(image)
        detections = YoloDetector(yolo_backend, models["yolo"]["size"], models["yolo"]["confidence"], models["yolo"]["iou"]).detect(image)
        print({"lane": lane, "detections": detections})
    finally:
        lane_backend.close(); yolo_backend.close()


def main(argv=None) -> int:
    args = parser().parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    config = load_config(args.config)
    if args.command == "run":
        SmartCarRuntime(config, args.dry_run, args.source, args.serial_port).run(args.max_frames)
    elif args.command == "manual":
        _manual(config, args)
    elif args.command == "camera-test":
        _camera_test(config, args)
    elif args.command == "model-test":
        _model_test(config, args)
    elif args.command == "serial-test":
        cfg = config["chassis"]
        with SerialController(args.serial_port or cfg["port"], cfg["baudrate"], cfg["timeout_s"], args.dry_run, tuple(cfg["motor_signs"])) as controller:
            print(controller.execute(ActionCommand("forward", args.rpm, duration_s=0.5, source="serial_test")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

