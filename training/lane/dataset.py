from __future__ import annotations

import csv
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cv2
import numpy as np
import torch
from torch.utils.data import Dataset

cv2.setNumThreads(0)
try:
    cv2.ocl.setUseOpenCL(False)
except AttributeError:
    pass


@dataclass(frozen=True)
class LaneRecord:
    image: Path
    binary_mask: Path
    instance_mask: Path
    split: str


def load_records(
    split_csv: Path,
    image_root: Path,
    binary_mask_root: Path,
    instance_mask_root: Path,
) -> list[LaneRecord]:
    records: list[LaneRecord] = []
    with split_csv.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        if "image" not in reader.fieldnames or "split" not in reader.fieldnames:
            raise ValueError("splits.csv must contain image and split columns.")
        for row in reader:
            image = image_root / row["image"]
            stem = Path(row["image"]).stem
            binary = first_existing(binary_mask_root, stem)
            instance = first_existing(instance_mask_root, stem)
            for path in (image, binary, instance):
                if not path.exists():
                    raise FileNotFoundError(path)
            records.append(
                LaneRecord(
                    image=image,
                    binary_mask=binary,
                    instance_mask=instance,
                    split=row["split"].strip().lower(),
                )
            )
    if not records:
        raise ValueError(f"No records loaded from {split_csv}")
    return records


def first_existing(root: Path, stem: str) -> Path:
    for suffix in (".png", ".jpg", ".jpeg", ".bmp"):
        path = root / f"{stem}{suffix}"
        if path.exists():
            return path
    return root / f"{stem}.png"


class LaneNetDataset(Dataset):
    def __init__(
        self,
        records: list[LaneRecord],
        width: int,
        height: int,
        normalize: str = "minus_one_to_one",
        augment: dict[str, Any] | None = None,
    ) -> None:
        self.records = records
        self.width = width
        self.height = height
        self.normalize = normalize
        self.augment = augment or {}

    def __len__(self) -> int:
        return len(self.records)

    def __getitem__(self, index: int) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        record = self.records[index]
        image = cv2.imread(str(record.image), cv2.IMREAD_COLOR)
        binary = cv2.imread(str(record.binary_mask), cv2.IMREAD_GRAYSCALE)
        instance = cv2.imread(str(record.instance_mask), cv2.IMREAD_GRAYSCALE)
        if image is None or binary is None or instance is None:
            raise FileNotFoundError(record)

        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        image = cv2.resize(image, (self.width, self.height), interpolation=cv2.INTER_AREA)
        binary = cv2.resize(binary, (self.width, self.height), interpolation=cv2.INTER_NEAREST)
        instance = cv2.resize(instance, (self.width, self.height), interpolation=cv2.INTER_NEAREST)

        image, binary, instance = self.apply_augmentations(image, binary, instance)
        image = image.astype(np.float32) / 255.0
        if self.normalize == "minus_one_to_one":
            image = image * 2.0 - 1.0
        elif self.normalize != "zero_to_one":
            raise ValueError(f"Unsupported normalization mode: {self.normalize}")
        binary = (binary > 127).astype(np.int64)
        instance = instance.astype(np.int64)

        return (
            torch.from_numpy(np.transpose(image, (2, 0, 1))),
            torch.from_numpy(binary),
            torch.from_numpy(instance),
        )

    def apply_augmentations(
        self,
        image: np.ndarray,
        binary: np.ndarray,
        instance: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        if not self.augment.get("enabled", False):
            return image, binary, instance

        flip_prob = float(self.augment.get("horizontal_flip_prob", 0.0))
        if flip_prob > 0 and random.random() < flip_prob:
            image = np.ascontiguousarray(image[:, ::-1])
            binary = np.ascontiguousarray(binary[:, ::-1])
            instance = np.ascontiguousarray(instance[:, ::-1])

        brightness = float(self.augment.get("brightness", 0.0))
        contrast = float(self.augment.get("contrast", 0.0))
        if brightness > 0 or contrast > 0:
            alpha = 1.0 + random.uniform(-contrast, contrast)
            beta = 255.0 * random.uniform(-brightness, brightness)
            image = np.clip(image.astype(np.float32) * alpha + beta, 0, 255).astype(np.uint8)

        return image, binary, instance
