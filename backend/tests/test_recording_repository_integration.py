"""Recording segment repository entegrasyon testleri."""

import unittest
from datetime import timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.database.database import Base
from src.infrastructure.database.repositories.recording_repository import SqlAlchemyRecordingSegmentRepository
from src.infrastructure.time_utils import utc_now


class RecordingRepositoryIntegrationTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
        self.repo = SqlAlchemyRecordingSegmentRepository(self.session)

    def tearDown(self):
        self.session.close()

    def test_add_and_list_segments_by_camera_and_time(self):
        now = utc_now()
        self.repo.add(RecordingSegment(
            id=None,
            camera_id=1,
            started_at=now - timedelta(minutes=10),
            ended_at=now - timedelta(minutes=9),
            recording_type="event",
            status="complete",
            file_path="C:/recordings/cam-1/event-1.mp4",
            file_sha256="abc123",
            size_bytes=2048,
            codec="h264",
            width=1920,
            height=1080,
            fps=25.0,
            alarm_id=7,
        ))
        self.repo.add(RecordingSegment(
            id=None,
            camera_id=2,
            started_at=now - timedelta(minutes=8),
            ended_at=now - timedelta(minutes=7),
            recording_type="continuous",
            status="complete",
            file_path="C:/recordings/cam-2/segment.mp4",
        ))

        segments = self.repo.list_segments(
            camera_id=1,
            since=now - timedelta(minutes=12),
            until=now - timedelta(minutes=1),
            limit=10,
        )

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].camera_id, 1)
        self.assertEqual(segments[0].recording_type, "event")
        self.assertEqual(segments[0].file_sha256, "abc123")
        self.assertEqual(segments[0].alarm_id, 7)

    def test_open_segment_overlaps_since_filter(self):
        now = utc_now()
        saved = self.repo.add(RecordingSegment(
            id=None,
            camera_id=1,
            started_at=now - timedelta(minutes=3),
            ended_at=None,
            recording_type="continuous",
            status="recording",
            file_path="C:/recordings/cam-1/open.mp4",
        ))

        segments = self.repo.list_segments(camera_id=1, since=now, limit=10)

        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].status, "recording")

        fetched = self.repo.get_by_id(saved.id or 0)
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.camera_id, 1)
        self.assertIsNone(self.repo.get_by_id(0))


if __name__ == "__main__":
    unittest.main()
