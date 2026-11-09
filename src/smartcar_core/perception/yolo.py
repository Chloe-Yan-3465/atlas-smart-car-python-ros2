from __future__ import annotations

from time import perf_counter

import cv2
import numpy as np

from ..inference import InferenceBackend
from ..types import Detection


LANDMARK_CLASSES = ("left", "right", "turnaround", "park", "person", "obstacle", "crosswalk")


def letterbox(image: np.ndarray, size: int = 640) -> tuple[np.ndarray, float, tuple[float, float]]:
    height, width = image.shape[:2]
    ratio = min(size / width, size / height)
    new_w, new_h = int(round(width * ratio)), int(round(height * ratio))
    resized = cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_LINEAR)
    dw, dh = (size - new_w) / 2.0, (size - new_h) / 2.0
    top, bottom = int(round(dh - 0.1)), int(round(dh + 0.1))
    left, right = int(round(dw - 0.1)), int(round(dw + 0.1))
    padded = cv2.copyMakeBorder(resized, top, bottom, left, right, cv2.BORDER_CONSTANT, value=(114, 114, 114))
    return padded, ratio, (dw, dh)


def preprocess_yolo(image: np.ndarray, size: int = 640) -> tuple[np.ndarray, float, tuple[float, float]]:
    padded, ratio, pad = letterbox(image, size)
    tensor = cv2.cvtColor(padded, cv2.COLOR_BGR2RGB).astype(np.float32) / 255.0
    return np.transpose(tensor, (2, 0, 1))[None], ratio, pad


def _iou(box: np.ndarray, boxes: np.ndarray) -> np.ndarray:
    x1, y1 = np.maximum(boxes[:, 0], box[0]), np.maximum(boxes[:, 1], box[1])
    x2, y2 = np.minimum(boxes[:, 2], box[2]), np.minimum(boxes[:, 3], box[3])
    inter = np.maximum(0, x2 - x1) * np.maximum(0, y2 - y1)
    area1 = np.maximum(0, box[2] - box[0]) * np.maximum(0, box[3] - box[1])
    area2 = np.maximum(0, boxes[:, 2] - boxes[:, 0]) * np.maximum(0, boxes[:, 3] - boxes[:, 1])
    return inter / np.maximum(area1 + area2 - inter, 1e-7)


def _nms(rows: np.ndarray, threshold: float) -> np.ndarray:
    if not len(rows):
        return rows
    kept = []
    for class_id in np.unique(rows[:, 5].astype(int)):
        current = rows[rows[:, 5].astype(int) == class_id]
        current = current[np.argsort(-current[:, 4])]
        while len(current):
            kept.append(current[0])
            current = current[1:][_iou(current[0, :4], current[1:, :4]) < threshold]
    return np.asarray(kept, dtype=np.float32)


def decode_yolo(output: np.ndarray, confidence: float, iou: float) -> np.ndarray:
    rows = np.squeeze(np.asarray(output))
    if rows.ndim != 2:
        raise ValueError(f"Unsupported YOLO output shape: {np.asarray(output).shape}")
    if rows.shape[1] == 6:  # ATC-exported/NMS: x1,y1,x2,y2,score,class
        return rows[rows[:, 4] >= confidence].astype(np.float32)
    if rows.shape[1] < 5 + len(LANDMARK_CLASSES):
        raise ValueError(f"YOLO output has too few columns: {rows.shape}")
    class_scores = rows[:, 5 : 5 + len(LANDMARK_CLASSES)] * rows[:, 4:5]
    class_ids = np.argmax(class_scores, axis=1)
    scores = class_scores[np.arange(len(rows)), class_ids]
    selected = rows[scores >= confidence, :4]
    scores, class_ids = scores[scores >= confidence], class_ids[scores >= confidence]
    boxes = np.empty_like(selected)
    boxes[:, 0] = selected[:, 0] - selected[:, 2] / 2
    boxes[:, 1] = selected[:, 1] - selected[:, 3] / 2
    boxes[:, 2] = selected[:, 0] + selected[:, 2] / 2
    boxes[:, 3] = selected[:, 1] + selected[:, 3] / 2
    return _nms(np.column_stack((boxes, scores, class_ids)), iou)


def scale_boxes(rows: np.ndarray, ratio: float, pad: tuple[float, float], shape: tuple[int, int]) -> np.ndarray:
    result = rows.copy()
    if not len(result):
        return result
    result[:, [0, 2]] = (result[:, [0, 2]] - pad[0]) / ratio
    result[:, [1, 3]] = (result[:, [1, 3]] - pad[1]) / ratio
    height, width = shape
    result[:, [0, 2]] = np.clip(result[:, [0, 2]], 0, width - 1)
    result[:, [1, 3]] = np.clip(result[:, [1, 3]], 0, height - 1)
    return result


class YoloDetector:
    def __init__(self, backend: InferenceBackend, size: int = 640, confidence: float = 0.35, iou: float = 0.45):
        self.backend, self.size, self.confidence, self.iou = backend, size, confidence, iou
        self.last_inference_ms = 0.0

    def detect(self, frame: np.ndarray) -> list[Detection]:
        tensor, ratio, pad = preprocess_yolo(frame, self.size)
        started = perf_counter()
        rows = decode_yolo(self.backend.infer(tensor)[0], self.confidence, self.iou)
        self.last_inference_ms = (perf_counter() - started) * 1000.0
        rows = scale_boxes(rows, ratio, pad, frame.shape[:2])
        return [Detection(int(r[5]), LANDMARK_CLASSES[int(r[5])], float(r[4]), *map(float, r[:4])) for r in rows if 0 <= int(r[5]) < len(LANDMARK_CLASSES)]

