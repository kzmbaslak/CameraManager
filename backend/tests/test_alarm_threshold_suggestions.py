"""Alarm threshold onerisi karar mantigi testleri."""

from types import SimpleNamespace
import unittest

from src.application.services.alarm_threshold_suggestions import build_threshold_suggestions


def alarm(camera_id: int, confidence: float | None, false_positive: bool) -> SimpleNamespace:
    return SimpleNamespace(
        camera_id=camera_id,
        confidence=confidence,
        false_positive=false_positive,
    )


class AlarmThresholdSuggestionTests(unittest.TestCase):
    def test_high_false_positive_rate_increases_threshold(self):
        suggestions = build_threshold_suggestions(
            [
                alarm(1, 0.60, True),
                alarm(1, 0.70, True),
                alarm(1, 0.80, False),
            ],
            minimum_samples=3,
        )

        self.assertEqual(len(suggestions), 1)
        self.assertEqual(suggestions[0].camera_id, 1)
        self.assertEqual(suggestions[0].false_positive_count, 2)
        self.assertEqual(suggestions[0].false_positive_rate, 0.667)
        self.assertEqual(suggestions[0].average_confidence, 0.7)
        self.assertEqual(suggestions[0].suggested_confidence_threshold, 0.8)

    def test_skips_cameras_below_minimum_sample_count(self):
        suggestions = build_threshold_suggestions(
            [
                alarm(1, 0.60, True),
                alarm(1, 0.70, True),
            ],
            minimum_samples=3,
        )

        self.assertEqual(suggestions, [])

    def test_zero_false_positive_with_enough_samples_keeps_threshold(self):
        suggestions = build_threshold_suggestions(
            [alarm(2, 0.75, False) for _ in range(10)],
            minimum_samples=3,
        )

        self.assertEqual(len(suggestions), 1)
        self.assertIsNone(suggestions[0].suggested_confidence_threshold)
        self.assertIn("korunabilir", suggestions[0].recommendation)

    def test_sorts_riskiest_camera_first(self):
        suggestions = build_threshold_suggestions(
            [
                alarm(1, 0.60, True),
                alarm(1, 0.60, True),
                alarm(1, 0.60, False),
                alarm(2, 0.50, True),
                alarm(2, 0.50, False),
                alarm(2, 0.50, False),
            ],
            minimum_samples=3,
        )

        self.assertEqual([item.camera_id for item in suggestions], [1, 2])


if __name__ == "__main__":
    unittest.main()
