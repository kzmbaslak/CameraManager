"""Kayit listeleme route filtre regresyon testleri."""

import os
import unittest
from datetime import datetime, timezone

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.domain.entities.recording_segment import RecordingSegment
from src.presentation.api.routes.recordings import list_recording_segments


class RecordingListFilterTests(unittest.TestCase):
    def _segment(self, segment_id: int, camera_id: int, alarm_id: int) -> RecordingSegment:
        return RecordingSegment(
            id=segment_id,
            camera_id=camera_id,
            started_at=datetime(2026, 7, 29, 10, segment_id, tzinfo=timezone.utc),
            ended_at=datetime(2026, 7, 29, 10, segment_id, 10, tzinfo=timezone.utc),
            recording_type="event",
            status="complete",
            file_path=f"C:/recordings/{segment_id}.mp4",
            alarm_id=alarm_id,
        )

    def test_alarm_id_filter_uses_alarm_segments_and_camera_filter(self):
        alarm_segments = [
            self._segment(1, 10, 99),
            self._segment(2, 11, 99),
        ]

        class UseCases:
            list_segments_called = False

            def list_alarm_segments(self, alarm_id):
                self.alarm_id = alarm_id
                return alarm_segments

            def list_segments(self, **kwargs):
                self.list_segments_called = True
                return []

        use_cases = UseCases()

        response = list_recording_segments(
            camera_id=10,
            alarm_id=99,
            limit=100,
            use_cases=use_cases,
            current_user={"sub": "operator1"},
        )

        self.assertEqual(use_cases.alarm_id, 99)
        self.assertFalse(use_cases.list_segments_called)
        self.assertEqual(response.total, 1)
        self.assertEqual(response.items[0].camera_id, 10)
        self.assertEqual(response.items[0].alarm_id, 99)


if __name__ == "__main__":
    unittest.main()
