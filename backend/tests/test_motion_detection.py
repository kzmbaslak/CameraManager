import os
import tempfile
import unittest

import numpy as np

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.application.use_cases.frame_processing_use_case import ProcessFrameUseCase
from src.domain.entities.alarm import AlarmType
from src.domain.entities.camera import Camera, CameraStatus


class FakeAlarmRepository:
    def __init__(self):
        self.alarms = []

    def get_latest_open(self, camera_id, alarm_type):
        return None

    def add(self, alarm):
        alarm.id = len(self.alarms) + 1
        self.alarms.append(alarm)
        return alarm


class MotionDetectionTests(unittest.TestCase):
    def test_motion_alarm_is_created_when_changed_area_exceeds_threshold(self):
        previous_ratio = os.environ.get("MOTION_DETECTION_MIN_CHANGED_RATIO")
        try:
            os.environ["MOTION_DETECTION_MIN_CHANGED_RATIO"] = "0.01"
            with tempfile.TemporaryDirectory() as tmp:
                alarm_repo = FakeAlarmRepository()
                use_case = ProcessFrameUseCase(
                    camera_repository=None,
                    alarm_repository=alarm_repo,
                    frame_source=None,
                    ai_service=None,
                    snapshot_dir=tmp,
                    cooldown_seconds=60,
                )
                camera = Camera(
                    id=1,
                    name="Cam",
                    host="127.0.0.1",
                    status=CameraStatus.ACTIVE,
                    motion_detection_enabled=True,
                )
                previous = np.zeros((120, 160, 3), dtype=np.uint8)
                current = previous.copy()
                current[20:90, 30:120] = 255

                result = use_case.analyze_motion_and_alarm(1, previous, current, camera=camera)

                self.assertIsNotNone(result.alarm)
                self.assertEqual(result.alarm.alarm_type, AlarmType.MOTION_DETECTED)
                self.assertGreater(result.motion_ratio, 0.01)
                self.assertEqual(len(alarm_repo.alarms), 1)
        finally:
            if previous_ratio is None:
                os.environ.pop("MOTION_DETECTION_MIN_CHANGED_RATIO", None)
            else:
                os.environ["MOTION_DETECTION_MIN_CHANGED_RATIO"] = previous_ratio

    def test_small_motion_does_not_create_alarm(self):
        previous_ratio = os.environ.get("MOTION_DETECTION_MIN_CHANGED_RATIO")
        try:
            os.environ["MOTION_DETECTION_MIN_CHANGED_RATIO"] = "0.2"
            with tempfile.TemporaryDirectory() as tmp:
                alarm_repo = FakeAlarmRepository()
                use_case = ProcessFrameUseCase(
                    camera_repository=None,
                    alarm_repository=alarm_repo,
                    frame_source=None,
                    ai_service=None,
                    snapshot_dir=tmp,
                    cooldown_seconds=60,
                )
                camera = Camera(
                    id=1,
                    name="Cam",
                    host="127.0.0.1",
                    status=CameraStatus.ACTIVE,
                    motion_detection_enabled=True,
                )
                previous = np.zeros((120, 160, 3), dtype=np.uint8)
                current = previous.copy()
                current[10:20, 10:20] = 255

                result = use_case.analyze_motion_and_alarm(1, previous, current, camera=camera)

                self.assertIsNone(result.alarm)
                self.assertEqual(len(alarm_repo.alarms), 0)
        finally:
            if previous_ratio is None:
                os.environ.pop("MOTION_DETECTION_MIN_CHANGED_RATIO", None)
            else:
                os.environ["MOTION_DETECTION_MIN_CHANGED_RATIO"] = previous_ratio


if __name__ == "__main__":
    unittest.main()
