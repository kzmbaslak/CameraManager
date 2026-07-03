from __future__ import annotations

from typing import Protocol

from src.domain.entities.camera import Camera


class IFrameSource(Protocol):
    def read_frame(self, camera: Camera) -> object | None:
        ...
