#!/usr/bin/env bash
set -euo pipefail

CONFIG="${CONFIG:-training/configs/yolov5.yaml}"
ARGS=(--config "$CONFIG")

if [ -n "${YOLOV5_DIR:-}" ]; then ARGS+=(--yolov5-dir "$YOLOV5_DIR"); fi
if [ -n "${WEIGHTS:-}" ]; then ARGS+=(--weights "$WEIGHTS"); fi
if [ -n "${IMG_SIZE:-}" ]; then ARGS+=(--img-size "$IMG_SIZE"); fi
if [ -n "${BATCH_SIZE:-}" ]; then ARGS+=(--batch-size "$BATCH_SIZE"); fi
if [ -n "${EPOCHS:-}" ]; then ARGS+=(--epochs "$EPOCHS"); fi
if [ -n "${DEVICE:-}" ]; then ARGS+=(--device "$DEVICE"); fi
if [ -n "${NAME:-}" ]; then ARGS+=(--name "$NAME"); fi

python training/landmark/train_smartcar.py "${ARGS[@]}" "$@"
