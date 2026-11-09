#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import yaml
from tqdm import tqdm

from dataset import LaneRecord, load_records
from model import build_lanenet_hnet


@dataclass
class FittedLane:
    k: float
    b: float
    pixels: int
    y_min: int
    y_max: int

    def x_at(self, y: float) -> float:
        return self.k * y + self.b


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate LaneNet checkpoint with lane-line postprocessing.")
    parser.add_argument("--config", default=Path("training/configs/lanenet.yaml"), type=Path)
    parser.add_argument("--checkpoint", default=Path("models/lane/runs/best.pth"), type=Path)
    parser.add_argument("--split", default="test", choices=["train", "val", "test"])
    parser.add_argument("--output-dir", default=Path("outputs/lane/postprocess"), type=Path)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--limit", default=128, type=int)
    parser.add_argument("--preview-count", default=48, type=int)
    parser.add_argument("--threshold", default=0.5, type=float)
    parser.add_argument("--morph-kernel", default=5, type=int)
    parser.add_argument("--min-area", default=80, type=int)
    parser.add_argument("--min-height", default=24, type=int)
    parser.add_argument("--max-lanes", default=4, type=int)
    return parser.parse_args()


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def load_model(checkpoint_path: Path, config: dict[str, Any], device: str) -> torch.nn.Module:
    checkpoint = torch.load(checkpoint_path, map_location=device)
    model_cfg = checkpoint.get("model_cfg", config["model"])
    model = build_lanenet_hnet(model_cfg).to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()
    return model


def preprocess(image_bgr: np.ndarray, width: int, height: int, normalize: str) -> torch.Tensor:
    image_rgb = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2RGB)
    image_rgb = cv2.resize(image_rgb, (width, height), interpolation=cv2.INTER_AREA)
    tensor = image_rgb.astype(np.float32) / 255.0
    if normalize == "minus_one_to_one":
        tensor = tensor * 2.0 - 1.0
    elif normalize != "zero_to_one":
        raise ValueError(f"Unsupported normalize mode: {normalize}")
    return torch.from_numpy(np.transpose(tensor, (2, 0, 1))[None, ...]).float()


def binary_mask_from_logits(logits: torch.Tensor, threshold: float) -> np.ndarray:
    if logits.shape[1] == 1:
        pred = (torch.sigmoid(logits[:, 0]) > threshold)[0]
    else:
        probs = torch.softmax(logits, dim=1)[:, 1]
        pred = (probs > threshold)[0]
    return pred.detach().cpu().numpy().astype(np.uint8)


def clean_mask(mask: np.ndarray, kernel_size: int) -> np.ndarray:
    if kernel_size <= 1:
        return mask.astype(np.uint8)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (kernel_size, kernel_size))
    cleaned = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    cleaned = cv2.dilate(cleaned, kernel, iterations=1)
    return cleaned


def fit_lanes(
    mask: np.ndarray,
    min_area: int,
    min_height: int,
    max_lanes: int,
) -> list[FittedLane]:
    num_labels, labels, stats, _centroids = cv2.connectedComponentsWithStats(mask.astype(np.uint8), connectivity=8)
    lanes: list[FittedLane] = []
    for label in range(1, num_labels):
        area = int(stats[label, cv2.CC_STAT_AREA])
        if area < min_area:
            continue
        ys, xs = np.where(labels == label)
        if len(xs) < 2:
            continue
        y_min = int(ys.min())
        y_max = int(ys.max())
        if y_max - y_min < min_height:
            continue
        try:
            k, b = np.polyfit(ys.astype(np.float32), xs.astype(np.float32), 1)
        except np.linalg.LinAlgError:
            continue
        lanes.append(FittedLane(k=float(k), b=float(b), pixels=area, y_min=y_min, y_max=y_max))

    lanes.sort(key=lambda lane: lane.pixels, reverse=True)
    return lanes[:max_lanes]


def lane_center_offset(lanes: list[FittedLane], width: int, height: int) -> tuple[float, bool]:
    if not lanes:
        return 0.0, False
    y = height - 1
    lanes_by_x = sorted(lanes, key=lambda lane: lane.x_at(y))
    if len(lanes_by_x) >= 2:
        left = lanes_by_x[0].x_at(y)
        right = lanes_by_x[-1].x_at(y)
        center = (left + right) / 2.0
    else:
        center = lanes_by_x[0].x_at(y)
    return float((center - width / 2.0) / (width / 2.0)), True


def draw_lanes(image: np.ndarray, lanes: list[FittedLane], color: tuple[int, int, int], thickness: int = 2) -> np.ndarray:
    canvas = image.copy()
    height, width = image.shape[:2]
    for lane in lanes:
        pt1 = (int(lane.x_at(lane.y_min)), lane.y_min)
        pt2 = (int(lane.x_at(lane.y_max)), lane.y_max)
        ok, clipped1, clipped2 = cv2.clipLine((0, 0, width, height), pt1, pt2)
        if ok:
            cv2.line(canvas, clipped1, clipped2, color, thickness, lineType=cv2.LINE_AA)
            mid = ((clipped1[0] + clipped2[0]) // 2, (clipped1[1] + clipped2[1]) // 2)
            cv2.putText(
                canvas,
                str(lane.pixels),
                mid,
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (255, 255, 0),
                1,
                lineType=cv2.LINE_AA,
            )
    return canvas


def overlay_mask(image: np.ndarray, mask: np.ndarray, color: tuple[int, int, int]) -> np.ndarray:
    overlay = image.copy()
    overlay[mask > 0] = (0.45 * overlay[mask > 0] + 0.55 * np.array(color)).astype(np.uint8)
    return overlay


def evaluate_record(
    record: LaneRecord,
    model: torch.nn.Module,
    device: str,
    width: int,
    height: int,
    normalize: str,
    args: argparse.Namespace,
) -> tuple[dict[str, Any], np.ndarray | None]:
    original = cv2.imread(str(record.image), cv2.IMREAD_COLOR)
    target = cv2.imread(str(record.binary_mask), cv2.IMREAD_GRAYSCALE)
    if original is None or target is None:
        raise FileNotFoundError(record.image)

    resized = cv2.resize(original, (width, height), interpolation=cv2.INTER_AREA)
    target = cv2.resize(target, (width, height), interpolation=cv2.INTER_NEAREST)
    target_mask = (target > 127).astype(np.uint8)

    tensor = preprocess(original, width, height, normalize).to(device)
    with torch.no_grad():
        logits, _embedding, _h = model(tensor)
    pred_mask = binary_mask_from_logits(logits, args.threshold)
    post_mask = clean_mask(pred_mask, args.morph_kernel)
    pred_lanes = fit_lanes(post_mask, args.min_area, args.min_height, args.max_lanes)
    target_lanes = fit_lanes(clean_mask(target_mask, args.morph_kernel), args.min_area, args.min_height, args.max_lanes)

    intersection = int(np.logical_and(pred_mask > 0, target_mask > 0).sum())
    union = int(np.logical_or(pred_mask > 0, target_mask > 0).sum())
    post_intersection = int(np.logical_and(post_mask > 0, target_mask > 0).sum())
    post_union = int(np.logical_or(post_mask > 0, target_mask > 0).sum())
    offset, offset_valid = lane_center_offset(pred_lanes, width, height)
    target_offset, target_offset_valid = lane_center_offset(target_lanes, width, height)
    offset_error = abs(offset - target_offset) if offset_valid and target_offset_valid else None

    row: dict[str, Any] = {
        "image": record.image.name,
        "raw_iou": intersection / max(union, 1),
        "post_iou": post_intersection / max(post_union, 1),
        "pred_lane_count": len(pred_lanes),
        "target_lane_count": len(target_lanes),
        "fit_success": int(len(pred_lanes) > 0),
        "two_lane_success": int(len(pred_lanes) >= 2),
        "offset": offset if offset_valid else "",
        "target_offset": target_offset if target_offset_valid else "",
        "offset_error": offset_error if offset_error is not None else "",
        "pred_pixels": int(pred_mask.sum()),
        "post_pixels": int(post_mask.sum()),
        "target_pixels": int(target_mask.sum()),
    }

    pred_vis = overlay_mask(resized, pred_mask, (0, 0, 255))
    post_vis = overlay_mask(resized, post_mask, (0, 255, 255))
    fit_vis = draw_lanes(post_vis, pred_lanes, (0, 255, 0), thickness=2)
    target_fit_vis = draw_lanes(overlay_mask(resized, target_mask, (255, 255, 255)), target_lanes, (255, 0, 0), thickness=2)
    panel = np.concatenate(
        [
            resized,
            cv2.cvtColor(target_mask * 255, cv2.COLOR_GRAY2BGR),
            pred_vis,
            fit_vis,
            target_fit_vis,
        ],
        axis=1,
    )
    return row, panel


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {}
    numeric = {}
    for key in ("raw_iou", "post_iou", "pred_lane_count", "fit_success", "two_lane_success", "pred_pixels", "target_pixels"):
        values = [float(row[key]) for row in rows if row[key] != ""]
        numeric[f"mean_{key}"] = float(np.mean(values)) if values else 0.0
    offset_errors = [float(row["offset_error"]) for row in rows if row["offset_error"] != ""]
    numeric["mean_offset_error"] = float(np.mean(offset_errors)) if offset_errors else None
    numeric["median_offset_error"] = float(np.median(offset_errors)) if offset_errors else None
    numeric["count"] = len(rows)
    return numeric


def main() -> None:
    args = parse_args()
    root = repo_root()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset_cfg = cfg["dataset"]
    model_cfg = cfg["model"]
    records = load_records(
        resolve_path(dataset_cfg["split_csv"], root),
        resolve_path(dataset_cfg["image_root"], root),
        resolve_path(dataset_cfg["binary_mask_root"], root),
        resolve_path(dataset_cfg["instance_mask_root"], root),
    )
    selected = [record for record in records if record.split == args.split]
    if args.limit > 0:
        selected = selected[: args.limit]
    if not selected:
        raise ValueError(f"No records for split={args.split}")

    width = int(model_cfg["input_width"])
    height = int(model_cfg["input_height"])
    normalize = str(model_cfg.get("normalize", "minus_one_to_one"))
    output_dir = resolve_path(args.output_dir, root)
    preview_dir = output_dir / "previews"
    output_dir.mkdir(parents=True, exist_ok=True)
    preview_dir.mkdir(parents=True, exist_ok=True)

    device = args.device
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA requested but torch.cuda.is_available() is false.")
    model = load_model(resolve_path(args.checkpoint, root), cfg, device)

    rows: list[dict[str, Any]] = []
    index_lines = ["# LaneNet Postprocess Preview", ""]
    for index, record in enumerate(tqdm(selected, desc="postprocess", disable=not sys.stderr.isatty())):
        row, panel = evaluate_record(record, model, device, width, height, normalize, args)
        rows.append(row)
        if index < args.preview_count and panel is not None:
            preview_name = f"{index:04d}_{record.image.stem}.jpg"
            cv2.imwrite(str(preview_dir / preview_name), panel)
            index_lines.append(
                f"- `{record.image.name}` raw_iou={row['raw_iou']:.3f} post_iou={row['post_iou']:.3f} "
                f"lanes={row['pred_lane_count']} offset_err={row['offset_error']}  "
                f"![](previews/{preview_name})"
            )

    metrics_path = output_dir / "metrics.csv"
    with metrics_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    summary = summarize(rows)
    (output_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    (output_dir / "index.md").write_text("\n".join(index_lines) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    print(f"Wrote previews to {preview_dir}")
    print(f"Wrote metrics to {metrics_path}")


if __name__ == "__main__":
    main()
