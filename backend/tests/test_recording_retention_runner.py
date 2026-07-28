"""Recording retention runner testleri."""

import os
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
from src.infrastructure.recording.retention import recording_prune_interval_minutes
from src.infrastructure.recording.retention_runner import RecordingRetentionRunner
from src.infrastructure.time_utils import utc_now


class RecordingRetentionRunnerTests(unittest.TestCase):
    def setUp(self):
        self._old_env = {
            "RECORDING_STORAGE_DIR": os.environ.get("RECORDING_STORAGE_DIR"),
            "RECORDING_RETENTION_DAYS": os.environ.get("RECORDING_RETENTION_DAYS"),
            "RECORDING_MAX_STORAGE_MB": os.environ.get("RECORDING_MAX_STORAGE_MB"),
            "RECORDING_PRUNE_INTERVAL_MINUTES": os.environ.get("RECORDING_PRUNE_INTERVAL_MINUTES"),
        }
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def tearDown(self):
        for key, value in self._old_env.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        self.engine.dispose()

    def test_prune_interval_env_allows_disabling_runner(self):
        os.environ["RECORDING_PRUNE_INTERVAL_MINUTES"] = "0"

        runner = RecordingRetentionRunner(interval_minutes=recording_prune_interval_minutes())

        self.assertFalse(runner.enabled)
        self.assertEqual(runner.interval_minutes, 0)

    def test_prune_interval_env_falls_back_on_invalid_value(self):
        os.environ["RECORDING_PRUNE_INTERVAL_MINUTES"] = "bad"

        self.assertEqual(recording_prune_interval_minutes(), 360)

    def test_run_once_removes_expired_segments(self):
        with tempfile.TemporaryDirectory() as tmp:
            os.environ["RECORDING_STORAGE_DIR"] = tmp
            os.environ["RECORDING_RETENTION_DAYS"] = "30"
            os.environ["RECORDING_MAX_STORAGE_MB"] = "0"
            path = Path(tmp) / "old.mp4"
            path.write_bytes(b"old")
            db = self.SessionLocal()
            try:
                repo = SqlAlchemyRecordingSegmentRepository(db)
                repo.add(RecordingSegment(
                    id=None,
                    camera_id=1,
                    started_at=utc_now() - timedelta(days=45, minutes=1),
                    ended_at=utc_now() - timedelta(days=45),
                    recording_type="event",
                    status="complete",
                    file_path=str(path),
                    size_bytes=3,
                ))
            finally:
                db.close()

            runner = RecordingRetentionRunner(
                db_session_factory=self.SessionLocal,
                recording_repository_factory=SqlAlchemyRecordingSegmentRepository,
                interval_minutes=360,
            )

            result = runner.run_once()

            self.assertEqual(result.removed_count, 1)
            self.assertEqual(result.deleted_db_count, 1)
            self.assertFalse(path.exists())


if __name__ == "__main__":
    unittest.main()
