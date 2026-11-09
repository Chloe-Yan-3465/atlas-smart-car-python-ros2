#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import torch
import yaml

from model import build_lanenet_hnet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Export LaneNet + H-Net checkpoint to ONNX.")
    parser.add_argument("--checkpoint", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path("training/configs/lanenet.yaml"))
    parser.add_argument("--height", default=256, type=int)
    parser.add_argument("--width", default=512, type=int)
    parser.add_argument("--opset", default=12, type=int)
    parser.add_argument("--skip-verify", action="store_true")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    checkpoint = torch.load(args.checkpoint, map_location="cpu")
    model_cfg = checkpoint.get("model_cfg", {})
    if not model_cfg and args.config.exists():
        model_cfg = (yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}).get("model", {})
    model = build_lanenet_hnet(model_cfg)
    model.load_state_dict(checkpoint["model"])
    model.eval()

    dummy = torch.rand(1, 3, args.height, args.width, dtype=torch.float32) * 2.0 - 1.0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    torch.onnx.export(
        model,
        dummy,
        args.output,
        dynamo=False,
        export_params=True,
        do_constant_folding=True,
        input_names=["input_image"],
        output_names=["binary_logits", "embeddings", "h_params"],
        opset_version=args.opset,
        dynamic_axes=None,
    )
    print(f"Exported {args.output}")
    if not args.skip_verify:
        verify_onnx(args.output, dummy)


def verify_onnx(path: Path, dummy: torch.Tensor) -> None:
    try:
        import onnx
        import onnxruntime as ort
    except ImportError:
        print("onnx or onnxruntime not installed; skipped ONNX verification.")
        return

    model = onnx.load(path)
    onnx.checker.check_model(model)
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    outputs = session.run(None, {session.get_inputs()[0].name: dummy.numpy().astype(np.float32)})
    print("ONNX verification passed.")
    for index, output in enumerate(outputs):
        print(f"  output[{index}] shape={output.shape} dtype={output.dtype}")


if __name__ == "__main__":
    main()
