#!/usr/bin/env bash
set -euo pipefail

YOLOV5_DIR="${YOLOV5_DIR:-external/yolov5}"
WEIGHTS="${WEIGHTS:-models/landmark/runs/incremental_v3/weights/best.pt}"
IMG_SIZE="${IMG_SIZE:-640}"
OUTPUT="${OUTPUT:-models/landmark/yolov5.onnx}"

if [ ! -f "$YOLOV5_DIR/export.py" ]; then
  echo "YOLOv5 not found. Run: bash training/landmark/fetch_yolov5.sh"
  exit 2
fi

python "$YOLOV5_DIR/export.py" \
  --weights "$WEIGHTS" \
  --img "$IMG_SIZE" \
  --batch 1 \
  --include onnx \
  --opset 12 \
  --simplify

EXPORTED="${WEIGHTS%.pt}.onnx"
mkdir -p "$(dirname "$OUTPUT")"
cp "$EXPORTED" "$OUTPUT"
echo "Exported $OUTPUT"

