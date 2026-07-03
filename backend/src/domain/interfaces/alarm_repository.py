from __future__ import annotations

from typing import Optional, Protocol, Sequence

from src.domain.entities.alarm import Alarm, AlarmStatus, AlarmType


class IAlarmRepository(Protocol):
    def add(self, alarm: Alarm) -> Alarm:
        ...

    def get_by_id(self, alarm_id: int) -> Alarm | None:
        ...

    def list_by_camera(self, camera_id: int, limit: int = 100) -> Sequence[Alarm]:
        ...

    def list_by_status(self, status: AlarmStatus, limit: int = 100) -> Sequence[Alarm]:
        ...

    def list_all(
        self,
        camera_id: Optional[int] = None,
        alarm_type: Optional[AlarmType] = None,
        status: Optional[AlarmStatus] = None,
        limit: int = 200,
    ) -> Sequence[Alarm]:
        ...

    def update(self, alarm: Alarm) -> Alarm:
        ...
