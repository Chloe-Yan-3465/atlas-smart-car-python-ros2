#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import os
import time
from pathlib import Path


DEFAULT_RUNS = Path("models/lane/runs")
ARTIFACTS = [
    "best.pth",
    "last.pth",
    "history.csv",
    "dataset_summary.json",
    "config.json",
    "previews/epoch_0001.jpg",
]
METRIC_KEYS = [
    "epoch",
    "lr",
    "train_loss",
    "train_binary_iou",
    "train_binary_acc",
    "val_loss",
    "val_binary_iou",
    "val_binary_acc",
    "seconds",
]


def latest_run(runs_dir: Path) -> Path:
    candidates = [path for path in runs_dir.iterdir() if path.is_dir()]
    if not candidates:
        raise FileNotFoundError(f"No LaneNet run directories found under {runs_dir}")
    return max(
        candidates,
        key=lambda p: (p / "history.csv").stat().st_mtime if (p / "history.csv").exists() else p.stat().st_mtime,
    )


def read_last_metrics(run_dir: Path) -> dict[str, str]:
    history = run_dir / "history.csv"
    if not history.exists():
        return {}
    last: dict[str, str] = {}
    with history.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            last = {key: value for key, value in row.items() if key is not None}
    return last


def print_status(run_dir: Path, runs_dir: Path) -> None:
    print(f"Run: {run_dir}")
    metrics = read_last_metrics(run_dir)
    if metrics:
        print("Latest metrics:")
        for key in METRIC_KEYS:
            if key in metrics:
                print(f"  {key}: {metrics[key]}")
    else:
        print("Latest metrics: history.csv not written yet")

    print("Artifacts:")
    for rel_path in ARTIFACTS:
        path = run_dir / rel_path
        marker = "ok" if path.exists() else "--"
        print(f"  [{marker}] {path}")
    preview_dir = run_dir / "previews"
    if preview_dir.exists():
        previews = sorted(preview_dir.glob("epoch_*.jpg"))
        if previews:
            print(f"  [ok] latest preview: {previews[-1]}")

    print("TensorBoard:")
    print(f"  tensorboard --logdir {runs_dir} --host 0.0.0.0 --port 6006")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Show LaneNet training status.")
    parser.add_argument("--runs-dir", type=Path, default=DEFAULT_RUNS)
    parser.add_argument("--run", type=Path)
    parser.add_argument("--watch", type=float, default=0.0)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    while True:
        try:
            run_dir = args.run or latest_run(args.runs_dir)
        except FileNotFoundError as exc:
            print(exc)
            print("Start a training run first, for example:")
            print("  python training/lane/train.py --config training/configs/lanenet.yaml --epochs 2")
            raise SystemExit(1) from exc
        if args.watch and os.isatty(1):
            print("\033[2J\033[H", end="")
        print_status(run_dir, args.runs_dir)
        if not args.watch:
            return
        time.sleep(args.watch)


if __name__ == "__main__":
    main()
