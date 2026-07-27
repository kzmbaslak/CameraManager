"""Recording retention ve disk kotasi temizligi testleri."""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.database.database import Base
from src.infrastructure.database.repositories.recording_repository import SqlAlchemyRecordingSegmentRepository
from src.infrastructure.recording.retention import RecordingRetentionService
from src.infrastructure.time_utils import utc_now


class RecordingRetentionTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        self.repo = SqlAlchemyRecordingSegmentRepository(self.session)
        self.tmp = tempfile.TemporaryDirectory()
        self.storage_root = Path(self.tmp.name)

    def tearDown(self):
        self.session.close()
        self.tmp.cleanup()

    def _add_file_segment(self, name: str, age_days: int, size: int) -> RecordingSegment:
        path = self.storage_root / name
        path.write_bytes(b"x" * size)
        now = utc_now()
        return self.repo.add(RecordingSegment(
            id=None,
            camera_id=1,
            started_at=now - timedelta(days=age_days, minutes=5),
            ended_at=now - timedelta(days=age_days),
            recording_type="continuous",
            status="complete",
            file_path=str(path),
            size_bytes=size,
        ))

    def test_prune_removes_old_segments_inside_storage_root(self):
        old_segment = self._add_file_segment("old.mp4", age_days=40, size=128)
        fresh_segment = self._add_file_segment("fresh.mp4", age_days=2, size=128)

        result = RecordingRetentionService(self.repo, self.storage_root).prune(retention_days=30, quota_mb=0)

        self.assertEqual(result.removed_count, 1)
        self.assertEqual(result.deleted_db_count, 1)
        self.assertFalse((self.storage_root / "old.mp4").exists())
        self.assertEqual([segment.id for segment in self.repo.list_segments(limit=10)], [fresh_segment.id])
        self.assertNotIn(old_segment.id, [segment.id for segment in self.repo.list_segments(limit=10)])

    def test_prune_skips_paths_outside_storage_root(self):
        outside = self.storage_root.parent / "outside-recording.mp4"
        outside.write_bytes(b"x")
        now = utc_now()
        self.repo.add(RecordingSegment(
            id=None,
            camera_id=1,
            started_at=now - timedelta(days=40, minutes=5),
            ended_at=now - timedelta(days=40),
            recording_type="continuous",
            status="complete",
            file_path=str(outside),
            size_bytes=1,
        ))
        try:
            result = RecordingRetentionService(self.repo, self.storage_root).prune(retention_days=30, quota_mb=0)

            self.assertEqual(result.removed_count, 0)
            self.assertEqual(result.skipped_count, 1)
            self.assertTrue(outside.exists())
            self.assertEqual(len(self.repo.list_segments(limit=10)), 1)
        finally:
            outside.unlink(missing_ok=True)

    def test_quota_prune_removes_oldest_until_under_limit(self):
        oldest = self._add_file_segment("oldest.mp4", age_days=5, size=800_000)
        self._add_file_segment("newest.mp4", age_days=1, size=800_000)

        result = RecordingRetentionService(self.repo, self.storage_root).prune(retention_days=365, quota_mb=1)

        remaining_ids = [segment.id for segment in self.repo.list_segments(limit=10)]
        self.assertEqual(result.removed_count, 1)
        self.assertNotIn(oldest.id, remaining_ids)
        self.assertFalse((self.storage_root / "oldest.mp4").exists())


if __name__ == "__main__":
    unittest.main()
