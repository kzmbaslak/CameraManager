"""Stream manager event clip recording tests."""

import os
import tempfile
import unittest
from datetime import datetime, timedelta

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.application.services.camera_stream_manager import CameraStreamManager
from src.infrastructure.database.database import Base
from src.infrastructure.database.repositories.recording_repository import SqlAlchemyRecordingSegmentRepository


class RecordingEventClipTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.session_factory = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.tmp = tempfile.TemporaryDirectory()
        self.previous_storage = os.environ.get("RECORDING_STORAGE_DIR")
        self.previous_fps = os.environ.get("RECORDING_EVENT_CLIP_FPS")
        self.previous_continuous_enabled = os.environ.get("RECORDING_CONTINUOUS_ENABLED")
        self.previous_continuous_fps = os.environ.get("RECORDING_CONTINUOUS_FPS")
        self.previous_active_start = os.environ.get("RECORDING_CONTINUOUS_ACTIVE_START")
        self.previous_active_end = os.environ.get("RECORDING_CONTINUOUS_ACTIVE_END")
        os.environ["RECORDING_STORAGE_DIR"] = self.tmp.name
        os.environ["RECORDING_EVENT_CLIP_FPS"] = "2"
        os.environ["RECORDING_CONTINUOUS_FPS"] = "2"

    def tearDown(self):
        if self.previous_storage is None:
            os.environ.pop("RECORDING_STORAGE_DIR", None)
        else:
            os.environ["RECORDING_STORAGE_DIR"] = self.previous_storage
        if self.previous_fps is None:
            os.environ.pop("RECORDING_EVENT_CLIP_FPS", None)
        else:
            os.environ["RECORDING_EVENT_CLIP_FPS"] = self.previous_fps
        if self.previous_continuous_enabled is None:
            os.environ.pop("RECORDING_CONTINUOUS_ENABLED", None)
        else:
            os.environ["RECORDING_CONTINUOUS_ENABLED"] = self.previous_continuous_enabled
        if self.previous_continuous_fps is None:
            os.environ.pop("RECORDING_CONTINUOUS_FPS", None)
        else:
            os.environ["RECORDING_CONTINUOUS_FPS"] = self.previous_continuous_fps
        if self.previous_active_start is None:
            os.environ.pop("RECORDING_CONTINUOUS_ACTIVE_START", None)
        else:
            os.environ["RECORDING_CONTINUOUS_ACTIVE_START"] = self.previous_active_start
        if self.previous_active_end is None:
            os.environ.pop("RECORDING_CONTINUOUS_ACTIVE_END", None)
        else:
            os.environ["RECORDING_CONTINUOUS_ACTIVE_END"] = self.previous_active_end
        self.tmp.cleanup()
        self.engine.dispose()

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

    def test_continuous_recording_schedule_handles_day_and_overnight_windows(self):
        manager = CameraStreamManager(ai_service=None)
        os.environ["RECORDING_CONTINUOUS_ACTIVE_START"] = "08:00"
        os.environ["RECORDING_CONTINUOUS_ACTIVE_END"] = "18:00"

        self.assertTrue(manager._continuous_recording_active_now(datetime(2026, 7, 28, 12, 0)))
        self.assertFalse(manager._continuous_recording_active_now(datetime(2026, 7, 28, 23, 0)))

        os.environ["RECORDING_CONTINUOUS_ACTIVE_START"] = "22:00"
        os.environ["RECORDING_CONTINUOUS_ACTIVE_END"] = "06:00"

        self.assertTrue(manager._continuous_recording_active_now(datetime(2026, 7, 28, 23, 0)))
        self.assertTrue(manager._continuous_recording_active_now(datetime(2026, 7, 28, 3, 0)))
        self.assertFalse(manager._continuous_recording_active_now(datetime(2026, 7, 28, 12, 0)))

    def test_continuous_recording_ignores_frames_outside_schedule(self):
        manager = CameraStreamManager(ai_service=None)
        os.environ["RECORDING_CONTINUOUS_ENABLED"] = "true"
        now = datetime.now()
        start = now + timedelta(hours=2)
        end = now + timedelta(hours=3)
        os.environ["RECORDING_CONTINUOUS_ACTIVE_START"] = start.strftime("%H:%M")
        os.environ["RECORDING_CONTINUOUS_ACTIVE_END"] = end.strftime("%H:%M")

        frame = np.zeros((32, 48, 3), dtype=np.uint8)
        manager._continuous_recording_buffers[5] = []
        manager._handle_continuous_recording_frame(camera_id=5, frame=frame)

        self.assertNotIn(5, manager._continuous_recording_buffers)

    def test_continuous_clip_writes_video_and_records_segment(self):
        manager = CameraStreamManager(
            ai_service=None,
            db_session_factory=self.session_factory,
            recording_repository_factory=SqlAlchemyRecordingSegmentRepository,
        )
        frames = [
            np.zeros((32, 48, 3), dtype=np.uint8),
            np.full((32, 48, 3), 200, dtype=np.uint8),
        ]

        manager._save_continuous_recording_clip_sync(camera_id=4, frames=frames)

        db = self.session_factory()
        try:
            repo = SqlAlchemyRecordingSegmentRepository(db)
            segments = list(repo.list_segments(camera_id=4, limit=10))
        finally:
            db.close()
        self.assertEqual(len(segments), 1)
        self.assertEqual(segments[0].recording_type, "continuous")
        self.assertIsNone(segments[0].alarm_id)
        self.assertEqual(segments[0].width, 48)
        self.assertEqual(segments[0].height, 32)
        self.assertEqual(segments[0].fps, 2.0)
        self.assertTrue(segments[0].file_sha256)
        self.assertGreater(segments[0].size_bytes or 0, 0)
        self.assertTrue(os.path.exists(segments[0].file_path))


if __name__ == "__main__":
    unittest.main()
