from __future__ import annotations

from typing import Protocol, Sequence

from src.domain.entities.camera import Camera


class ICameraRepository(Protocol):
    def add(self, camera: Camera) -> Camera:
        ...

    def get_by_id(self, camera_id: int) -> Camera | None:
        ...

    def list_all(self) -> Sequence[Camera]:
        ...

    def list_by_nvr(self, nvr_id: int) -> Sequence[Camera]:
        ...

    def update(self, camera: Camera) -> Camera:
        ...

    def delete(self, camera_id: int) -> None:
        ...
