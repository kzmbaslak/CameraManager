"""Insan yogunlugu anomali karar kurali testleri."""

import unittest
from datetime import timedelta

from src.application.services.person_density_policy import PersonDensityPolicy
from src.domain.entities.person_analytics import CameraPersonHourlyStat
from src.infrastructure.time_utils import utc_now


def make_bucket(hours_ago: int, peak: int, total: int | None = None) -> CameraPersonHourlyStat:
    hour_start = utc_now().replace(minute=0, second=0, microsecond=0) - timedelta(hours=hours_ago)
    return CameraPersonHourlyStat(
        id=None,
        camera_id=1,
        hour_start=hour_start,
        detection_samples=1,
        total_person_count=total if total is not None else peak,
        max_person_count=peak,
        max_confidence=0.9,
        first_detected_at=hour_start,
        last_detected_at=hour_start,
    )


class PersonDensityPolicyTests(unittest.TestCase):
    def test_absolute_peak_triggers_without_baseline(self):
        policy = PersonDensityPolicy(absolute_peak_person_count=4, min_baseline_buckets=6)

        result = policy.evaluate(make_bucket(0, peak=4), [])

        self.assertTrue(result.triggered)
        self.assertEqual(result.reason, "absolute_peak")

    def test_baseline_multiplier_triggers_when_current_hour_is_unusual(self):
        policy = PersonDensityPolicy(
            absolute_peak_person_count=20,
            min_baseline_buckets=3,
            baseline_multiplier=3.0,
            min_current_peak_person_count=2,
        )
        previous = [make_bucket(ago, peak=1) for ago in (1, 2, 3)]

        result = policy.evaluate(make_bucket(0, peak=4), previous)

        self.assertTrue(result.triggered)
        self.assertEqual(result.reason, "baseline_multiplier")
        self.assertAlmostEqual(result.baseline_peak_average or 0.0, 1.0)

    def test_insufficient_baseline_does_not_trigger_below_absolute_peak(self):
        policy = PersonDensityPolicy(absolute_peak_person_count=10, min_baseline_buckets=4)

        result = policy.evaluate(make_bucket(0, peak=3), [make_bucket(1, peak=1)])

        self.assertFalse(result.triggered)
        self.assertEqual(result.reason, "insufficient_baseline")


if __name__ == "__main__":
    unittest.main()
