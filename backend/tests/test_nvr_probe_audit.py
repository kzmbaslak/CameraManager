"""NVR kanal tarama audit metadata regresyon testleri."""

import os
import unittest
from unittest.mock import patch

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.presentation.api.routes.nvrs import _audit_nvr_probe
from src.presentation.api.schemas.nvr_schema import NVRChannelInfo, NVRProbeDiagnostics


class NVRProbeAuditTests(unittest.TestCase):
    def test_probe_audit_writes_redacted_summary(self):
        class Client:
            host = "10.0.0.20"

        class Request:
            client = Client()

        diagnostics = NVRProbeDiagnostics(
            source="rtsp_fallback",
            onvif_ok=False,
            fallback_used=True,
            profile_count=0,
            stream_uri_count=0,
            onvif_error="rtsp://admin:secret@192.168.1.10/stream",
            fallback_error="password=secret",
            channels=[
                NVRChannelInfo(
                    profile_token="profile-1",
                    profile_name="Main",
                    rtsp_url="rtsp://admin:secret@192.168.1.10/stream",
                    source="rtsp_fallback",
                )
            ],
        )

        with patch("src.presentation.api.routes.nvrs.write_audit_event") as audit:
            _audit_nvr_probe(Request(), {"sub": "operator1"}, 42, diagnostics)

        audit.assert_called_once()
        action = audit.call_args.args[0]
        kwargs = audit.call_args.kwargs
        self.assertEqual(action, "nvr.probe")
        self.assertEqual(kwargs["actor"], "operator1")
        self.assertEqual(kwargs["source_ip"], "10.0.0.20")
        metadata = kwargs["metadata"]
        self.assertEqual(metadata["nvr_id"], 42)
        self.assertEqual(metadata["source"], "rtsp_fallback")
        self.assertFalse(metadata["onvif_ok"])
        self.assertTrue(metadata["fallback_used"])
        self.assertEqual(metadata["channel_count"], 1)
        self.assertNotIn("secret", str(metadata))
        self.assertNotIn("rtsp://", str(metadata))


if __name__ == "__main__":
    unittest.main()
