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
            )
        }
        os.environ["JWT_SECRET_KEY"] = "test-jwt-secret-key-with-more-than-32-characters"
        os.environ["CAMERA_ENCRYPTION_KEY"] = "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY="
        os.environ["CORS_ALLOWED_ORIGINS"] = "https://console.example.local"
        os.environ["TRUSTED_HOSTS"] = "console.example.local"
        os.environ["AUDIT_CHAIN_SECRET"] = "test-audit-chain-secret-with-more-than-32"
        os.environ["AUTH_COOKIE_MODE"] = "secure"

        engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(bind=engine)
        self.session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()

    def tearDown(self):
        self.session.close()
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
        self.assertTrue(any(check["key"] == "migration_script_inventory" for check in result["setup_checks"]))
        self.assertTrue(any("cihaz parolasi kayitli degil" in item["message"] for item in result["findings"]))
        self.assertFalse(any("HttpOnly/SameSite secure cookie" in item["message"] for item in result["findings"]))


if __name__ == "__main__":
    unittest.main()
