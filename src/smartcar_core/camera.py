from __future__ import annotations

from pathlib import Path
from time import monotonic

import cv2


class CameraSource:
    def __init__(self, source: str | int, width: int = 1280, height: int = 720, fps: int = 30, loop: bool = False):
        self.source, self.loop = source, loop
        self._images: list[Path] = []
        self._index = 0
        path = Path(str(source))
        if path.is_dir():
            self._images = sorted(p for p in path.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"})
            if not self._images:
                raise FileNotFoundError(f"No images found in {path}")
            self.capture = None
        else:
            device = int(source) if str(source).isdigit() else str(source)
            self.capture = cv2.VideoCapture(device, cv2.CAP_V4L2 if isinstance(device, str) and device.startswith("/dev/") else cv2.CAP_ANY)
            self.capture.set(cv2.CAP_PROP_FRAME_WIDTH, width)
            self.capture.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
            self.capture.set(cv2.CAP_PROP_FPS, fps)
            self.capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
            if not self.capture.isOpened():
                raise RuntimeError(f"Cannot open camera source {source}")
        self.last_frame_at = 0.0

    def read(self):
        if self._images:
            if self._index >= len(self._images):
                if not self.loop:
                    return False, None
                self._index = 0
            frame = cv2.imread(str(self._images[self._index]))
            self._index += 1
            ok = frame is not None
        else:
            ok, frame = self.capture.read()
        if ok:
            self.last_frame_at = monotonic()
        return ok, frame

    def close(self):
        if self.capture is not None:
            self.capture.release()

