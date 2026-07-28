"""Stream manager event clip recording tests."""

import os
import tempfile
import unittest

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.application.services.camera_stream_manager import CameraStreamManager
from src.infrastructure.database.database import Base
from src.infrastructure.database.repositories.recording_repository import SqlAlchemyRecordingSegmentRepository


class RecordingEventClipTests(unittest.TestCase):
    def setUp(self):
        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_storage = os.environ.get("RECORDING_STORAGE_DIR")
        self.previous_fps = os.environ.get("RECORDING_EVENT_CLIP_FPS")
        os.environ["RECORDING_STORAGE_DIR"] = self.tmp.name
        os.environ["RECORDING_EVENT_CLIP_FPS"] = "2"

    def tearDown(self):
        if self.previous_storage is None:
            os.environ.pop("RECORDING_STORAGE_DIR", None)
        else:
            os.environ["RECORDING_STORAGE_DIR"] = self.previous_storage
        if self.previous_fps is None:
            os.environ.pop("RECORDING_EVENT_CLIP_FPS", None)
        else:
            os.environ["RECORDING_EVENT_CLIP_FPS"] = self.previous_fps
        self.tmp.cleanup()

    def test_event_clip_writes_video_and_records_segment(self):
        manager = CameraStreamManager(
            ai_service=None,
            db_session_factory=self.session_factory,
            recording_repository_factory=SqlAlchemyRecordingSegmentRepository,
        )
        frames = [
            np.zeros((32, 48, 3), dtype=np.uint8),
            np.full((32, 48, 3), 128, dtype=np.uint8),
        ]

        manager._save_event_recording_clip_sync(camera_id=3, alarm_id=9, frames=frames, detection_payload={
            "frame_width": 48,
            "frame_height": 32,
            "detected_at": "2026-07-28T10:00:00Z",
            "detections": [{
                "label": "person",
                "confidence": 0.91,
                "bounding_box": {"x": 5, "y": 6, "width": 12, "height": 18},
            }],
        })

        db = self.session_factory()
        try:
            repo = SqlAlchemyRecordingSegmentRepository(db)
            segments = list(repo.list_segments(camera_id=3, limit=10))
        finally:
            db.close()
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].recording_type, "event")
        self.assertEqual(segments[0].alarm_id, 9)
        self.assertEqual(segments[0].width, 48)
        self.assertEqual(segments[0].height, 32)
        self.assertEqual(segments[0].fps, 2.0)
        self.assertTrue(segments[0].file_sha256)
        self.assertGreater(segments[0].size_bytes or 0, 0)
        self.assertTrue(os.path.exists(segments[0].file_path))
        metadata_path = os.path.splitext(segments[0].file_path)[0] + ".detections.json"
        self.assertTrue(os.path.exists(metadata_path))
        with open(metadata_path, "r", encoding="utf-8") as file:
            self.assertIn('"confidence":0.91', file.read())


if __name__ == "__main__":
    unittest.main()
