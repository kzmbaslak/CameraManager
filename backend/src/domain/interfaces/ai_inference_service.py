from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, Sequence

from src.domain.entities.alarm import BoundingBox


@dataclass(frozen=True)
class Detection:
    label: str
    confidence: float
    bounding_box: BoundingBox


class IAIInferenceService(Protocol):
    def detect_humans(
        self,
        frame: object,
        conf_threshold: float | None = None,
        iou_threshold: float | None = None,
    ) -> Sequence[Detection]:
        ...
