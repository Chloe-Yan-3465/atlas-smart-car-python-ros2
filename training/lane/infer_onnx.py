#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def preprocess(image: np.ndarray, width: int, height: int, normalize: str) -> np.ndarray:
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    image = cv2.resize(image, (width, height), interpolation=cv2.INTER_AREA)
    tensor = image.astype(np.float32) / 255.0
    if normalize == "minus_one_to_one":
        tensor = tensor * 2.0 - 1.0
    elif normalize != "zero_to_one":
        raise ValueError(f"Unsupported normalize mode: {normalize}")
    return np.transpose(tensor, (2, 0, 1))[None, ...].astype(np.float32)


def lane_mask(binary_logits: np.ndarray) -> np.ndarray:
    logits = np.squeeze(binary_logits)
    if logits.ndim == 3 and logits.shape[0] == 2:
        mask = np.argmax(logits, axis=0).astype(np.uint8)
    elif logits.ndim == 2:
        mask = (1.0 / (1.0 + np.exp(-logits)) > 0.5).astype(np.uint8)
    else:
        raise ValueError(f"Unsupported binary_logits shape: {binary_logits.shape}")
    return mask * 255


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LaneNet ONNX on images and write mask previews.")
    parser.add_argument("--model", required=True, type=Path)
    parser.add_argument("--images", required=True, type=Path)
    parser.add_argument("--output-dir", default=Path("reports/lanenet_onnx_preview"), type=Path)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--height", default=256, type=int)
    parser.add_argument("--normalize", default="minus_one_to_one", choices=["minus_one_to_one", "zero_to_one"])
    parser.add_argument("--limit", default=32, type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    import onnxruntime as ort

    image_paths = sorted(
        path for path in args.images.rglob("*") if path.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}
    )
    if args.limit > 0:
        image_paths = image_paths[: args.limit]
    if not image_paths:
        raise FileNotFoundError(args.images)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    session = ort.InferenceSession(str(args.model), providers=["CPUExecutionProvider"])
    input_name = session.get_inputs()[0].name
    rows = ["# LaneNet ONNX Preview", ""]
    for image_path in image_paths:
        frame = cv2.imread(str(image_path), cv2.IMREAD_COLOR)
        if frame is None:
            continue
        tensor = preprocess(frame, args.width, args.height, args.normalize)
        outputs = session.run(None, {input_name: tensor})
        pred = lane_mask(outputs[0])
        resized = cv2.resize(frame, (args.width, args.height), interpolation=cv2.INTER_AREA)
        overlay = resized.copy()
        overlay[pred > 0] = (0.5 * overlay[pred > 0] + 0.5 * np.array([0, 0, 255])).astype(np.uint8)
        panel = np.concatenate([resized, cv2.cvtColor(pred, cv2.COLOR_GRAY2BGR), overlay], axis=1)
        out_name = f"{image_path.stem}_preview.jpg"
        cv2.imwrite(str(args.output_dir / out_name), panel)
        rows.append(f"- `{image_path.name}`: ![]({out_name})")
    (args.output_dir / "index.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"Wrote {len(rows) - 2} previews to {args.output_dir}")


if __name__ == "__main__":
    main()
