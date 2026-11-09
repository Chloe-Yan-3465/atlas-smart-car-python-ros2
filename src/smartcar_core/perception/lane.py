from __future__ import annotations

from time import monotonic, perf_counter

import cv2
import numpy as np

from ..inference import InferenceBackend
from ..types import LaneResult


def preprocess_lane(image: np.ndarray, width: int = 512, height: int = 256) -> np.ndarray:
    rgb = cv2.cvtColor(cv2.resize(image, (width, height)), cv2.COLOR_BGR2RGB)
    tensor = rgb.astype(np.float32) / 127.5 - 1.0
    return np.transpose(tensor, (2, 0, 1))[None].astype(np.float32)


def lane_mask(output: np.ndarray) -> np.ndarray:
    logits = np.squeeze(np.asarray(output))
    if logits.ndim == 3 and logits.shape[0] >= 2:
        return (np.argmax(logits[:2], axis=0) == 1).astype(np.uint8)
    if logits.ndim == 3 and logits.shape[-1] >= 2:
        return (np.argmax(logits[..., :2], axis=-1) == 1).astype(np.uint8)
    if logits.ndim == 2:
        return (logits > (0.0 if logits.min() < 0 else 0.5)).astype(np.uint8)
    raise ValueError(f"Unsupported lane output shape: {np.asarray(output).shape}")


def lane_from_mask(mask: np.ndarray, min_pixels: int = 80, roi_start: float = 0.55) -> LaneResult:
    binary = np.asarray(mask).astype(bool)
    height, width = binary.shape
    start = max(0, min(height - 1, int(height * roi_start)))
    ys, xs = np.nonzero(binary[start:])
    if xs.size < min_pixels:
        return LaneResult(valid=False)
    center = float(np.median(xs)) / max(width - 1, 1)
    steering = float(np.clip((center - 0.5) * 2.0, -1.0, 1.0))
    density = float(xs.size) / float((height - start) * width)
    return LaneResult(True, steering, center, min(1.0, density * 20.0))


class LaneDetector:
    def __init__(self, backend: InferenceBackend, width: int = 512, height: int = 256, min_pixels: int = 80):
        self.backend, self.width, self.height, self.min_pixels = backend, width, height, min_pixels

    def detect(self, frame: np.ndarray) -> LaneResult:
        started = perf_counter()
        outputs = self.backend.infer(preprocess_lane(frame, self.width, self.height))
        result = lane_from_mask(lane_mask(outputs[0]), self.min_pixels)
        result.timestamp = monotonic()
        result.inference_ms = (perf_counter() - started) * 1000.0
        return result

