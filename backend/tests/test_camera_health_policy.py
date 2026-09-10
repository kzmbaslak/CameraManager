"""Camera health threshold policy tests."""

import os
import unittest

from src.application.services.camera_health_checker import CameraHealthChecker
from src.application.services.camera_health_policy import CameraHealthPolicy
from src.domain.entities.alarm import AlarmSeverity


class _Sample:
    def __init__(self, reachable=True, latency_ms=None):
        self.reachable = reachable
        self.latency_ms = latency_ms


class CameraHealthPolicyTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = {
            key: os.environ.get(key)
            for key in (
                "CAMERA_HEALTH_CRITICAL_AVAILABILITY_PERCENT",
                "CAMERA_HEALTH_WARNING_AVAILABILITY_PERCENT",
                "CAMERA_HEALTH_MAX_LATENCY_MS",
                "CAMERA_HEALTH_STALE_SAMPLE_SECONDS",
            )
        }

    def tearDown(self):
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_policy_loads_and_clamps_environment_values(self):
        os.environ["CAMERA_HEALTH_CRITICAL_AVAILABILITY_PERCENT"] = "99"
        os.environ["CAMERA_HEALTH_WARNING_AVAILABILITY_PERCENT"] = "80"
        os.environ["CAMERA_HEALTH_MAX_LATENCY_MS"] = "5"
        os.environ["CAMERA_HEALTH_STALE_SAMPLE_SECONDS"] = "99999"

        policy = CameraHealthPolicy.from_environment()

        self.assertEqual(policy.critical_availability_percent, 80.0)
        self.assertEqual(policy.warning_availability_percent, 99.0)
        self.assertEqual(policy.max_latency_ms, 50.0)
        self.assertEqual(policy.stale_sample_seconds, 3600)

    def test_checker_uses_policy_thresholds_for_degraded_alarm(self):
        checker = CameraHealthChecker(health_policy=CameraHealthPolicy(max_latency_ms=250.0))

        degraded, message, severity = checker._health_degradation([_Sample(latency_ms=300.0)])

        self.assertTrue(degraded)
        self.assertIn("yuksek latency 300", message)
        self.assertEqual(severity, AlarmSeverity.MEDIUM)
