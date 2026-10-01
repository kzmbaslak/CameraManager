"""Kamera sabotaj/karartma analiz politikasi testleri."""

import os
import tempfile
import unittest

import numpy as np

from src.application.services.camera_stream_manager import CameraStreamManager
from src.application.services.camera_tamper_policy import CameraTamperPolicy
from src.domain.entities.alarm import AlarmType
from src.domain.entities.camera import CameraStatus


class FakeDb:
    def close(self):
        pass


class FakeCamera:
    status = CameraStatus.ACTIVE


class FakeCameraRepository:
    def get_by_id(self, camera_id):
        return FakeCamera()


class FakeAlarmRepository:
    def __init__(self):
        self.added = []

    def get_latest_open(self, camera_id, alarm_type):
        return None

    def add(self, alarm):
        self.added.append(alarm)
        alarm.id = len(self.added)
        return alarm


class CameraTamperPolicyTests(unittest.TestCase):
    def test_dark_frame_triggers_tamper_signal(self):
        policy = CameraTamperPolicy(dark_mean_threshold=12.0, blur_variance_threshold=0.0)
        frame = np.zeros((64, 64, 3), dtype=np.uint8)

        result = policy.analyze(frame)

        self.assertTrue(result.triggered)
        self.assertEqual(result.reason, "dark_frame")

    def test_textured_frame_is_normal(self):
        policy = CameraTamperPolicy(
            dark_mean_threshold=12.0,
            flat_stddev_threshold=2.0,
            blur_variance_threshold=1.0,
        )
        rng = np.random.default_rng(42)
        frame = rng.integers(0, 256, size=(64, 64, 3), dtype=np.uint8)

        result = policy.analyze(frame)

        self.assertFalse(result.triggered)
        self.assertEqual(result.reason, "normal")

    def test_stream_manager_creates_alarm_after_consecutive_suspicious_frames(self):
        alarm_repo = FakeAlarmRepository()
        previous_snapshot_dir = os.environ.get("SNAPSHOT_DIR")
        with tempfile.TemporaryDirectory() as temp_dir:
            os.environ["SNAPSHOT_DIR"] = temp_dir
            manager = CameraStreamManager(
                ai_service=None,
                db_session_factory=FakeDb,
                camera_repository_factory=lambda db: FakeCameraRepository(),
                alarm_repository_factory=lambda db: alarm_repo,
            )
            manager._camera_tamper_policy = CameraTamperPolicy(
                frame_stride=1,
                consecutive_frames=2,
                dark_mean_threshold=12.0,
                blur_variance_threshold=0.0,
                alarm_cooldown_seconds=60,
            )
            frame = np.zeros((64, 64, 3), dtype=np.uint8)

            first_alarm, _ = manager._detect_tamper_and_alarm_sync(5, frame)
            second_alarm, _ = manager._detect_tamper_and_alarm_sync(5, frame)

            self.assertIsNone(first_alarm)
            self.assertIsNotNone(second_alarm)
            self.assertEqual(alarm_repo.added[0].alarm_type, AlarmType.CAMERA_TAMPERED)
            self.assertTrue(alarm_repo.added[0].snapshot_path)
        if previous_snapshot_dir is None:
            os.environ.pop("SNAPSHOT_DIR", None)
        else:
            os.environ["SNAPSHOT_DIR"] = previous_snapshot_dir


if __name__ == "__main__":
    unittest.main()
