"""Recording retention and disk quota cleanup helpers."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import timedelta
from pathlib import Path

from src.domain.entities.recording_segment import RecordingSegment
from src.domain.interfaces.recording_repository import IRecordingSegmentRepository
from src.infrastructure.time_utils import utc_now

BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_RECORDING_DIR = BACKEND_DIR / "data" / "recordings"


@dataclass
class RecordingPruneResult:
    """Recording cleanup sonucu."""

    retention_days: int
    quota_mb: int
    removed_count: int = 0
    removed_bytes: int = 0
    deleted_db_count: int = 0
    skipped_count: int = 0
    removed_filenames: list[str] = field(default_factory=list)
    skipped_reasons: list[str] = field(default_factory=list)


def recording_storage_dir() -> Path:
    """Kayit kok dizinini env veya varsayilandan cozer."""
    return Path(os.environ.get("RECORDING_STORAGE_DIR", str(DEFAULT_RECORDING_DIR))).resolve()


def recording_retention_days() -> int:
    """Recording retention gun ayarini guvenli araliga sikistirir."""
    try:
        value = int(os.environ.get("RECORDING_RETENTION_DAYS", "30") or "30")
    except ValueError:
        value = 30
    return min(max(value, 1), 3650)


def recording_quota_mb() -> int:
    """Recording disk kotasi MB ayarini okur; 0 kota kontrolunu kapatir."""
    try:
        value = int(os.environ.get("RECORDING_MAX_STORAGE_MB", "0") or "0")
    except ValueError:
        value = 0
    return max(value, 0)


def recording_prune_interval_minutes() -> int:
    """Otomatik recording prune periyodunu okur; 0 otomatik calistiriciyi kapatir."""
    try:
        value = int(os.environ.get("RECORDING_PRUNE_INTERVAL_MINUTES", "360") or "360")
    except ValueError:
        value = 360
    return min(max(value, 0), 10_080)


class RecordingRetentionService:
    """Kayit segmentleri icin retention ve disk kotasi temizligi uygular."""

    def __init__(self, repository: IRecordingSegmentRepository, storage_root: Path | None = None):
        self._repository = repository
        self._storage_root = (storage_root or recording_storage_dir()).resolve()

    def prune(self, retention_days: int | None = None, quota_mb: int | None = None) -> RecordingPruneResult:
        effective_retention = recording_retention_days() if retention_days is None else min(max(retention_days, 1), 3650)
        effective_quota = recording_quota_mb() if quota_mb is None else max(quota_mb, 0)
        result = RecordingPruneResult(retention_days=effective_retention, quota_mb=effective_quota)

        cutoff = utc_now() - timedelta(days=effective_retention)
        retention_candidates = list(self._repository.list_completed_before(cutoff, limit=5000))
        self._remove_segments(retention_candidates, result)

        if effective_quota > 0:
            quota_bytes = effective_quota * 1024 * 1024
            remaining = list(self._repository.list_completed_oldest(limit=5000))
            current_size = sum(max(segment.size_bytes or self._safe_file_size(segment), 0) for segment in remaining)
            quota_candidates: list[RecordingSegment] = []
            for segment in remaining:
                if current_size <= quota_bytes:
                    break
                segment_size = max(segment.size_bytes or self._safe_file_size(segment), 0)
                quota_candidates.append(segment)
                current_size -= segment_size
            self._remove_segments(quota_candidates, result)

        return result

    def _remove_segments(self, segments: list[RecordingSegment], result: RecordingPruneResult) -> None:
        delete_ids: list[int] = []
        for segment in segments:
            path = Path(segment.file_path).resolve()
            if not self._is_inside_storage(path):
                result.skipped_count += 1
                result.skipped_reasons.append(f"storage disi path: segment {segment.id}")
                continue
            size = max(segment.size_bytes or self._file_size(path), 0)
            try:
                if path.exists():
                    path.unlink()
                if segment.id:
                    delete_ids.append(segment.id)
                result.removed_count += 1
                result.removed_bytes += size
                result.removed_filenames.append(path.name)
            except OSError as exc:
                result.skipped_count += 1
                result.skipped_reasons.append(f"silinemedi: segment {segment.id}: {exc}")
        result.deleted_db_count += self._repository.delete_by_ids(delete_ids)

    def _is_inside_storage(self, path: Path) -> bool:
        try:
            path.relative_to(self._storage_root)
            return True
        except ValueError:
            return False

    def _safe_file_size(self, segment: RecordingSegment) -> int:
        path = Path(segment.file_path).resolve()
        if not self._is_inside_storage(path):
            return 0
        return self._file_size(path)

    @staticmethod
    def _file_size(path: Path) -> int:
        try:
            return path.stat().st_size if path.exists() else 0
        except OSError:
            return 0
