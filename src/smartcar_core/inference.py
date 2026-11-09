from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Sequence

import numpy as np


class InferenceBackend(ABC):
    @abstractmethod
    def infer(self, tensor: np.ndarray) -> list[np.ndarray]: ...

    def close(self) -> None:
        return None


class OnnxBackend(InferenceBackend):
    def __init__(self, model_path: str | Path, providers: Sequence[str] | None = None):
        try:
            import onnxruntime as ort
        except ImportError as exc:
            raise RuntimeError("Install the CPU extra: pip install -e '.[cpu]'") from exc
        self.session = ort.InferenceSession(
            str(model_path), providers=list(providers or ["CPUExecutionProvider"])
        )
        self.input_name = self.session.get_inputs()[0].name

    def infer(self, tensor: np.ndarray) -> list[np.ndarray]:
        return [np.asarray(v) for v in self.session.run(None, {self.input_name: tensor})]


class AscendBackend(InferenceBackend):
    """Thin lazy wrapper around ais-bench; CANN provides this dependency on Atlas."""

    def __init__(self, model_path: str | Path, device_id: int = 0):
        try:
            from ais_bench.infer.interface import InferSession
        except ImportError as exc:
            raise RuntimeError("ais_bench is missing; source the Atlas CANN environment first") from exc
        self.session = InferSession(device_id, str(model_path))

    def infer(self, tensor: np.ndarray) -> list[np.ndarray]:
        return [np.asarray(v) for v in self.session.infer([np.ascontiguousarray(tensor)])]

    def close(self) -> None:
        finalize = getattr(self.session, "finalize", None)
        if callable(finalize):
            finalize()


def create_backend(kind: str, model_path: str | Path, device_id: int = 0) -> InferenceBackend:
    path = Path(model_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    normalized = kind.lower()
    if normalized == "onnx":
        return OnnxBackend(path)
    if normalized in {"om", "ascend"}:
        return AscendBackend(path, device_id=device_id)
    raise ValueError(f"Unsupported inference backend: {kind}")

