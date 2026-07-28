"""Recording retention icin uygulama ici periyodik calistirici."""

from __future__ import annotations

import asyncio
import logging

from src.infrastructure.recording.retention import (
    RecordingRetentionService,
    recording_prune_interval_minutes,
)
from src.infrastructure.security.audit_logger import write_audit_event

logger = logging.getLogger(__name__)


class RecordingRetentionRunner:
    """Tamamlanmis kayit segmentlerinde retention/kota temizligini periyodik uygular."""

    def __init__(
        self,
        db_session_factory=None,
        recording_repository_factory=None,
        interval_minutes: int | None = None,
    ):
        self._db_session_factory = db_session_factory
        self._recording_repository_factory = recording_repository_factory
        self._interval_minutes = recording_prune_interval_minutes() if interval_minutes is None else interval_minutes
        self._task: asyncio.Task | None = None

    @property
    def interval_minutes(self) -> int:
        return self._interval_minutes

    @property
    def enabled(self) -> bool:
        return self._interval_minutes > 0

    def start(self) -> None:
        """Arka plan prune dongusunu baslatir; interval 0 ise calismaz."""
        if not self.enabled:
            logger.info("[RecordingRetention] Otomatik kayit temizligi kapali.")
            return
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self._loop(), name="recording_retention_runner")
            logger.info("[RecordingRetention] Otomatik kayit temizligi baslatildi: %s dk.", self._interval_minutes)

    def stop(self) -> None:
        """Arka plan prune dongusunu durdurur."""
        if self._task and not self._task.done():
            self._task.cancel()

    def run_once(self):
        """Tek seferlik prune calistirir ve sonucu dondurur."""
        if self._db_session_factory is None or self._recording_repository_factory is None:
            raise RuntimeError("RecordingRetentionRunner DB/repository factory yapilandirilmamis.")
        db = self._db_session_factory()
        try:
            repository = self._recording_repository_factory(db)
            result = RecordingRetentionService(repository).prune()
            if result.removed_count or result.skipped_count:
                write_audit_event(
                    "recording.prune.automatic",
                    actor="system",
                    metadata={
                        "retention_days": result.retention_days,
                        "quota_mb": result.quota_mb,
                        "removed_count": result.removed_count,
                        "removed_bytes": result.removed_bytes,
                        "deleted_db_count": result.deleted_db_count,
                        "skipped_count": result.skipped_count,
                    },
                )
            return result
        finally:
            db.close()

    async def _loop(self) -> None:
        try:
            while True:
                try:
                    await asyncio.get_event_loop().run_in_executor(None, self.run_once)
                except Exception as exc:
                    logger.warning("[RecordingRetention] Otomatik prune hatasi: %s", exc)
                await asyncio.sleep(self._interval_minutes * 60)
        except asyncio.CancelledError:
            pass
