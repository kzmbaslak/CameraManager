"""Stream manager insan yogunlugu alarm entegrasyonu testleri."""

import unittest
from datetime import timedelta

from src.application.services.camera_stream_manager import CameraStreamManager
from src.application.services.person_density_policy import PersonDensityPolicy
from src.domain.entities.alarm import AlarmType
from src.domain.entities.person_analytics import CameraPersonHourlyStat
from src.infrastructure.time_utils import utc_now


class FakeDb:
    def close(self):
        pass


class FakePersonAnalyticsRepository:
    def __init__(self):
        self.bucket = None
        self.pruned_days = None

    def record_detection(self, camera_id, detected_at, person_count, max_confidence):
        hour_start = detected_at.replace(minute=0, second=0, microsecond=0)
        self.bucket = CameraPersonHourlyStat(
            id=1,
            camera_id=camera_id,
            hour_start=hour_start,
            detection_samples=1,
            total_person_count=person_count,
            max_person_count=person_count,
            max_confidence=max_confidence,
            first_detected_at=detected_at,
            last_detected_at=detected_at,
        )
        return self.bucket

    def list_hourly(self, camera_id, since, until, limit=168):
        base = (self.bucket.hour_start if self.bucket else utc_now()).replace(minute=0, second=0, microsecond=0)
        return [
            CameraPersonHourlyStat(
                id=index,
                camera_id=camera_id,
                hour_start=base - timedelta(hours=index + 1),
                detection_samples=1,
                total_person_count=1,
                max_person_count=1,
                max_confidence=0.6,
                first_detected_at=base - timedelta(hours=index + 1),
                last_detected_at=base - timedelta(hours=index + 1),
            )
            for index in range(6)
        ]

    def prune_older_than(self, days=30):
        self.pruned_days = days
        return 0


class FakeAlarmRepository:
    def __init__(self):
        self.added = []

    def get_latest_open(self, camera_id, alarm_type):
        return None

    def add(self, alarm):
        self.added.append(alarm)
        alarm.id = len(self.added)
        return alarm


class PersonDensityAlarmIntegrationTests(unittest.TestCase):
    def test_record_person_analytics_creates_density_alarm(self):
        analytics_repo = FakePersonAnalyticsRepository()
        alarm_repo = FakeAlarmRepository()
        manager = CameraStreamManager(
            ai_service=None,
            db_session_factory=FakeDb,
            alarm_repository_factory=lambda db: alarm_repo,
            person_analytics_repository_factory=lambda db: analytics_repo,
        )
        manager._person_density_policy = PersonDensityPolicy(
            absolute_peak_person_count=4,
            min_baseline_buckets=3,
            baseline_multiplier=3.0,
            alarm_cooldown_seconds=60,
        )

        manager._record_person_analytics_sync(
            12,
            {
                "detected_at": utc_now().isoformat() + "Z",
                "detections": [{"confidence": 0.8} for _ in range(4)],
            },
        )

        self.assertEqual(len(alarm_repo.added), 1)
        self.assertEqual(alarm_repo.added[0].alarm_type, AlarmType.PERSON_DENSITY_ANOMALY)
        self.assertIn("Olagan disi insan yogunlugu", alarm_repo.added[0].message)


if __name__ == "__main__":
    unittest.main()
