#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
import yaml
from torch import nn
from torch.utils.data import DataLoader
from tqdm import tqdm

from dataset import LaneNetDataset, load_records
from losses import LaneNetLoss
from model import build_lanenet_hnet


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Train LaneNet + H-Net.")
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    parser.add_argument("--resume", type=Path)
    parser.add_argument(
        "--pretrained",
        type=Path,
        help="Load model weights only and start a fresh optimizer/scheduler run.",
    )
    parser.add_argument("--epochs", type=int)
    parser.add_argument("--batch-size", type=int)
    parser.add_argument("--workers", type=int)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def seed_everything(seed: int) -> None:
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)
        torch.backends.cudnn.benchmark = True


def tensorboard_writer(output_dir: Path):
    try:
        from torch.utils.tensorboard import SummaryWriter
    except ImportError:
        return None
    return SummaryWriter(log_dir=str(output_dir / "tensorboard"))


def resolve_path(path: str | Path, root: Path) -> Path:
    value = Path(path)
    return value if value.is_absolute() else root / value


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def run_epoch(
    model: nn.Module,
    loader: DataLoader,
    criterion: LaneNetLoss,
    device: str,
    optimizer: torch.optim.Optimizer | None = None,
    log_period: int = 0,
) -> dict[str, float]:
    training = optimizer is not None
    model.train(training)
    loss_sum = torch.zeros((), device=device)
    sample_count = 0
    intersection_sum = torch.zeros((), device=device)
    union_sum = torch.zeros((), device=device)
    correct_sum = torch.zeros((), device=device)
    pixel_sum = torch.zeros((), device=device)
    total_batches = len(loader)
    show_progress = sys.stderr.isatty()
    if log_period <= 0 and not show_progress:
        log_period = 100
    if log_period > 0:
        print(f"{'train' if training else 'val'} batches={total_batches}", flush=True)
    non_blocking = device.startswith("cuda")
    for batch_index, (images, binary_masks, instance_masks) in enumerate(
        tqdm(loader, leave=False, disable=not show_progress),
        start=1,
    ):
        images = images.to(device, non_blocking=non_blocking)
        binary_masks = binary_masks.to(device, non_blocking=non_blocking)
        instance_masks = instance_masks.to(device, non_blocking=non_blocking)
        with torch.set_grad_enabled(training):
            binary_logits, embeddings, h_params = model(images)
            loss = criterion(binary_logits, embeddings, h_params, binary_masks, instance_masks)
            if training:
                optimizer.zero_grad(set_to_none=True)
                loss.backward()
                optimizer.step()
        batch_size = images.shape[0]
        with torch.no_grad():
            loss_sum += loss.detach() * batch_size
            sample_count += batch_size
            counts = binary_metric_counts(binary_logits.detach(), binary_masks.detach())
            intersection_sum += counts["intersection"]
            union_sum += counts["union"]
            correct_sum += counts["correct"]
            pixel_sum += counts["pixels"]
        if log_period > 0 and batch_index % log_period == 0:
            current_loss = loss_sum / max(sample_count, 1)
            current_iou = intersection_sum / torch.clamp(union_sum, min=1.0)
            print(
                f"{'train' if training else 'val'} batch={batch_index}/{total_batches} "
                f"loss={float(current_loss.item()):.4f} iou={float(current_iou.item()):.4f}",
                flush=True,
            )
    loss_avg = loss_sum / max(sample_count, 1)
    binary_iou = intersection_sum / torch.clamp(union_sum, min=1.0)
    binary_acc = correct_sum / torch.clamp(pixel_sum, min=1.0)
    return {
        "loss": float(loss_avg.item()),
        "binary_iou": float(binary_iou.item()),
        "binary_acc": float(binary_acc.item()),
    }


def binary_metric_counts(binary_logits: torch.Tensor, binary_masks: torch.Tensor) -> dict[str, torch.Tensor]:
    if binary_logits.shape[1] == 1:
        pred = (torch.sigmoid(binary_logits[:, 0]) > 0.5).long()
    else:
        pred = torch.argmax(binary_logits, dim=1)
    target = binary_masks.long()
    lane_pred = pred == 1
    lane_target = target == 1
    intersection = torch.logical_and(lane_pred, lane_target).sum().float()
    union = torch.logical_or(lane_pred, lane_target).sum().float()
    correct = (pred == target).sum().float()
    pixels = torch.tensor(target.numel(), device=target.device, dtype=torch.float32)
    return {"intersection": intersection, "union": union, "correct": correct, "pixels": pixels}


def class_distribution(records) -> dict[str, int]:
    counts = {"records": len(records), "lane_pixels": 0, "background_pixels": 0}
    for record in records[: min(len(records), 256)]:
        mask = cv2.imread(str(record.binary_mask), cv2.IMREAD_GRAYSCALE)
        if mask is None:
            continue
        lane = int((mask > 127).sum())
        counts["lane_pixels"] += lane
        counts["background_pixels"] += int(mask.size - lane)
    return counts


def append_history(path: Path, row: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        if not exists:
            writer.writeheader()
        writer.writerow(row)


def save_preview(
    model: nn.Module,
    dataset: LaneNetDataset,
    output_dir: Path,
    epoch: int,
    device: str,
    count: int = 4,
) -> None:
    if len(dataset) == 0:
        return
    model.eval()
    preview_dir = output_dir / "previews"
    preview_dir.mkdir(parents=True, exist_ok=True)
    indices = list(range(min(count, len(dataset))))
    panels = []
    with torch.no_grad():
        for index in indices:
            image, target, _instance = dataset[index]
            logits, _embeddings, _h = model(image.unsqueeze(0).to(device))
            if logits.shape[1] == 1:
                pred = (torch.sigmoid(logits[0, 0]).cpu().numpy() > 0.5).astype(np.uint8) * 255
            else:
                pred = torch.argmax(logits[0], dim=0).cpu().numpy().astype(np.uint8) * 255
            image_np = np.transpose(image.numpy(), (1, 2, 0))
            if dataset.normalize == "minus_one_to_one":
                image_np = (image_np + 1.0) / 2.0
            image_np = np.clip(image_np * 255.0, 0, 255).astype(np.uint8)
            target_np = target.numpy().astype(np.uint8) * 255
            overlay = image_np.copy()
            overlay[pred > 0] = (0.5 * overlay[pred > 0] + 0.5 * np.array([255, 0, 0])).astype(np.uint8)
            panel = np.concatenate(
                [
                    cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR),
                    cv2.cvtColor(target_np, cv2.COLOR_GRAY2BGR),
                    cv2.cvtColor(pred, cv2.COLOR_GRAY2BGR),
                    cv2.cvtColor(overlay, cv2.COLOR_RGB2BGR),
                ],
                axis=1,
            )
            panels.append(panel)
    if panels:
        cv2.imwrite(str(preview_dir / f"epoch_{epoch:04d}.jpg"), np.concatenate(panels, axis=0))


def load_checkpoint(path: Path, model: nn.Module, optimizer, scheduler, device: str) -> tuple[int, float]:
    checkpoint = torch.load(path, map_location=device)
    model.load_state_dict(checkpoint["model"])
    if optimizer is not None and checkpoint.get("optimizer"):
        optimizer.load_state_dict(checkpoint["optimizer"])
    if scheduler is not None and checkpoint.get("scheduler"):
        scheduler.load_state_dict(checkpoint["scheduler"])
    return int(checkpoint.get("epoch", 0)), float(checkpoint.get("best_val_loss", checkpoint.get("val_loss", float("inf"))))


def load_pretrained(path: Path, model: nn.Module, device: str) -> None:
    checkpoint = torch.load(path, map_location=device)
    state_dict = checkpoint.get("model", checkpoint)
    model.load_state_dict(state_dict)


def dataloader_worker_kwargs(num_workers: int) -> dict[str, Any]:
    if num_workers <= 0:
        return {}
    return {"prefetch_factor": 2}


def main() -> None:
    args = parse_args()
    if args.resume and args.pretrained:
        raise ValueError("--resume and --pretrained are mutually exclusive.")

    root = repo_root()
    cfg = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset_cfg = cfg["dataset"]
    model_cfg = cfg["model"]
    train_cfg = cfg["train"]
    loss_cfg = cfg.get("loss", {})
    augment_cfg = cfg.get("augment", {})

    if args.epochs is not None:
        train_cfg["epochs"] = args.epochs
    if args.batch_size is not None:
        train_cfg["batch_size"] = args.batch_size
    if args.workers is not None:
        train_cfg["workers"] = args.workers
    if args.output_dir is not None:
        train_cfg["output_dir"] = str(args.output_dir)
    seed_everything(int(train_cfg.get("seed", 42)))

    records = load_records(
        resolve_path(dataset_cfg["split_csv"], root),
        resolve_path(dataset_cfg["image_root"], root),
        resolve_path(dataset_cfg["binary_mask_root"], root),
        resolve_path(dataset_cfg["instance_mask_root"], root),
    )
    train_records = [r for r in records if r.split == "train"]
    val_records = [r for r in records if r.split == "val"]
    if not train_records or not val_records:
        raise ValueError("Need at least one train and one val record in splits.csv.")

    width = int(model_cfg["input_width"])
    height = int(model_cfg["input_height"])
    normalize = str(model_cfg.get("normalize", "minus_one_to_one"))
    train_ds = LaneNetDataset(
        train_records,
        width=width,
        height=height,
        normalize=normalize,
        augment=augment_cfg,
    )
    val_ds = LaneNetDataset(val_records, width=width, height=height, normalize=normalize)

    output_dir = resolve_path(train_cfg["output_dir"], root)
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "config.json").write_text(json.dumps(cfg, indent=2, ensure_ascii=False), encoding="utf-8")

    summary = {
        "train_records": len(train_records),
        "val_records": len(val_records),
        "test_records": len([r for r in records if r.split == "test"]),
        "input_width": width,
        "input_height": height,
        "normalize": normalize,
        "model_cfg": model_cfg,
        "train_distribution_sample": class_distribution(train_records),
        "val_distribution_sample": class_distribution(val_records),
    }
    (output_dir / "dataset_summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if args.dry_run:
        return

    device = args.device
    if device.startswith("cuda") and not torch.cuda.is_available():
        raise RuntimeError("CUDA device requested but torch.cuda.is_available() is false.")

    train_workers = int(train_cfg.get("workers", 4))
    val_workers = max(0, train_workers // 2)
    train_loader = DataLoader(
        train_ds,
        batch_size=int(train_cfg["batch_size"]),
        shuffle=True,
        num_workers=train_workers,
        pin_memory=device.startswith("cuda"),
        **dataloader_worker_kwargs(train_workers),
    )
    val_loader = DataLoader(
        val_ds,
        batch_size=int(train_cfg["batch_size"]),
        shuffle=False,
        num_workers=val_workers,
        pin_memory=device.startswith("cuda"),
        **dataloader_worker_kwargs(val_workers),
    )

    model = build_lanenet_hnet(model_cfg).to(device)
    criterion = LaneNetLoss(
        binary_mode=str(loss_cfg.get("binary_mode", "ce")),
        embedding_weight=float(loss_cfg.get("embedding_weight", 0.1)),
        hnet_weight=float(loss_cfg.get("hnet_weight", 0.001)),
        lane_class_weight=float(loss_cfg.get("lane_class_weight", 3.0)),
    ).to(device)
    optimizer = torch.optim.AdamW(
        model.parameters(),
        lr=float(train_cfg["learning_rate"]),
        weight_decay=float(train_cfg.get("weight_decay", 0.0002)),
    )
    scheduler = torch.optim.lr_scheduler.StepLR(
        optimizer,
        step_size=int(train_cfg.get("lr_step_size", 20)),
        gamma=float(train_cfg.get("lr_gamma", 0.5)),
    )

    best_val = float("inf")
    start_epoch = 0
    if args.resume:
        start_epoch, best_val = load_checkpoint(args.resume, model, optimizer, scheduler, device)
        print(f"Resumed from {args.resume}: start_epoch={start_epoch}, best_val_loss={best_val:.4f}")
    elif args.pretrained:
        load_pretrained(args.pretrained, model, device)
        print(f"Loaded pretrained model weights from {args.pretrained}")

    writer = tensorboard_writer(output_dir)
    history_path = output_dir / "history.csv"
    for epoch in range(start_epoch + 1, int(train_cfg["epochs"]) + 1):
        started = time.time()
        print(f"epoch={epoch} train_start", flush=True)
        train_metrics = run_epoch(
            model,
            train_loader,
            criterion,
            device,
            optimizer,
            int(train_cfg.get("log_period", 0)),
        )
        print(f"epoch={epoch} val_start", flush=True)
        val_metrics = run_epoch(
            model,
            val_loader,
            criterion,
            device,
            log_period=int(train_cfg.get("log_period", 0)),
        )
        scheduler.step()
        elapsed = time.time() - started
        row = {
            "epoch": epoch,
            "lr": optimizer.param_groups[0]["lr"],
            "train_loss": train_metrics["loss"],
            "train_binary_iou": train_metrics["binary_iou"],
            "train_binary_acc": train_metrics["binary_acc"],
            "val_loss": val_metrics["loss"],
            "val_binary_iou": val_metrics["binary_iou"],
            "val_binary_acc": val_metrics["binary_acc"],
            "seconds": elapsed,
        }
        append_history(history_path, row)
        if writer is not None:
            for key, value in row.items():
                if key != "epoch":
                    writer.add_scalar(key, float(value), epoch)
        print(
            "epoch={epoch} train_loss={train_loss:.4f} val_loss={val_loss:.4f} "
            "val_iou={val_iou:.4f} val_acc={val_acc:.4f} lr={lr:.6g} seconds={seconds:.1f}".format(
                epoch=epoch,
                train_loss=train_metrics["loss"],
                val_loss=val_metrics["loss"],
                val_iou=val_metrics["binary_iou"],
                val_acc=val_metrics["binary_acc"],
                lr=optimizer.param_groups[0]["lr"],
                seconds=elapsed,
            )
        )
        if epoch == 1 or epoch % int(train_cfg.get("preview_period", 5)) == 0:
            save_preview(model, val_ds, output_dir, epoch, device, int(train_cfg.get("preview_count", 4)))

        checkpoint = {
            "epoch": epoch,
            "model": model.state_dict(),
            "model_cfg": model_cfg,
            "optimizer": optimizer.state_dict(),
            "scheduler": scheduler.state_dict(),
            "val_loss": val_metrics["loss"],
            "best_val_loss": min(best_val, val_metrics["loss"]),
            "history": row,
        }
        torch.save(checkpoint, output_dir / "last.pth")
        if val_metrics["loss"] < best_val:
            best_val = val_metrics["loss"]
            torch.save(checkpoint, output_dir / "best.pth")
        save_period = int(train_cfg.get("save_period", 0))
        if save_period > 0 and epoch % save_period == 0:
            torch.save(checkpoint, output_dir / f"epoch_{epoch:04d}.pth")
    if writer is not None:
        writer.close()


if __name__ == "__main__":
    main()
