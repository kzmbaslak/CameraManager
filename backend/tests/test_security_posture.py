"""Security posture cihaz sertlestirme ozet testleri."""

import os
import unittest

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from src.domain.entities.camera import CameraStatus
from src.infrastructure.database.database import Base
from src.infrastructure.database.models import CameraModel, NVRModel


class SecurityPostureTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = {
            key: os.environ.get(key)
            for key in (
                "JWT_SECRET_KEY",
                "CAMERA_ENCRYPTION_KEY",
                "CORS_ALLOWED_ORIGINS",
                "TRUSTED_HOSTS",
                "AUDIT_CHAIN_SECRET",
                "AUTH_COOKIE_MODE",
                "BACKUP_EXTERNAL_ARCHIVE_DIR",
                "CAMERA_HEALTH_CRITICAL_AVAILABILITY_PERCENT",
                "CAMERA_HEALTH_WARNING_AVAILABILITY_PERCENT",
                "CAMERA_HEALTH_MAX_LATENCY_MS",
                "CAMERA_HEALTH_STALE_SAMPLE_SECONDS",
            )
        }
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-with-more-than-32-characters"
        os.environ["CAMERA_ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://console.example.local"
        os.environ["TRUSTED_HOSTS"] = "console.example.local"
        os.environ["AUDIT_CHAIN_SECRET"] = "test-audit-chain-secret-with-more-than-32"
        os.environ["AUTH_COOKIE_MODE"] = "secure"
        os.environ["BACKUP_EXTERNAL_ARCHIVE_DIR"] = r"C:\secure-backups"
        os.environ["CAMERA_HEALTH_CRITICAL_AVAILABILITY_PERCENT"] = "85"
        os.environ["CAMERA_HEALTH_WARNING_AVAILABILITY_PERCENT"] = "96"
        os.environ["CAMERA_HEALTH_MAX_LATENCY_MS"] = "1500"
        os.environ["CAMERA_HEALTH_STALE_SAMPLE_SECONDS"] = "180"

        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=self.engine)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)()

    def tearDown(self):
        self.session.close()
        self.engine.dispose()
        for key, value in self._env_backup.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value

    def test_security_posture_reports_device_hardening_counts(self):
        self.session.add(CameraModel(
            name="Gate",
            host="10.0.0.10",
            rtsp_port=554,
            onvif_port=80,
            encrypted_password="encrypted",
            status=CameraStatus.ACTIVE,
            onvif_ptz_supported=True,
        ))
        self.session.add(CameraModel(
            name="Yard",
            host="10.0.0.11",
            rtsp_port=8554,
            onvif_port=8080,
            encrypted_password="",
            status=CameraStatus.ACTIVE,
        ))
        self.session.add(NVRModel(
            name="Recorder",
            host="10.0.0.20",
            onvif_port=80,
            encrypted_password=None,
        ))
        self.session.commit()

        from src.presentation.api import security_posture

        result = security_posture(current_user={"role": "admin"}, db=self.session)

        self.assertEqual(result["device_total_count"], 3)
        self.assertEqual(result["device_without_password_count"], 2)
        self.assertEqual(result["camera_without_password_count"], 1)
        self.assertEqual(result["nvr_without_password_count"], 1)
        self.assertEqual(result["camera_default_rtsp_port_count"], 1)
        self.assertEqual(result["device_default_onvif_port_count"], 2)
        self.assertEqual(result["camera_onvif_capability_unknown_count"], 2)
        self.assertEqual(result["camera_ptz_supported_count"], 1)
        self.assertIn("active_failed_login_key_count", result)
        self.assertIn("active_failed_login_attempt_count", result)
        self.assertIn("failed_login_limit", result)
        self.assertIn("failed_login_window_seconds", result)
        self.assertTrue(result["secure_cookie_auth"])
        self.assertTrue(result["backup_external_archive_configured"])
        self.assertEqual(result["camera_health_critical_availability_percent"], 85.0)
        self.assertEqual(result["camera_health_warning_availability_percent"], 96.0)
        self.assertEqual(result["camera_health_max_latency_ms"], 1500.0)
        self.assertEqual(result["camera_health_stale_sample_seconds"], 180)
        self.assertTrue(any(check["key"] == "migration_script_inventory" for check in result["setup_checks"]))
        self.assertTrue(any("cihaz parolasi kayitli degil" in item["message"] for item in result["findings"]))
        self.assertFalse(any("HttpOnly/SameSite secure cookie" in item["message"] for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
