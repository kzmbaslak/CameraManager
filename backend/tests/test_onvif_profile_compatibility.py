"""ONVIF profile compatibility inference tests."""

import unittest

from src.domain.interfaces.camera_probe_service import CameraProbeResult
from src.infrastructure.onvif.onvif_probe_service import ONVIFProbeService


class OnvifProfileCompatibilityTests(unittest.TestCase):
    def test_infers_profile_s_t_and_m_indicators_from_capabilities_and_streams(self):
        result = ONVIFProbeService.infer_profile_compatibility(
            {
                "media_supported": True,
                "events_supported": True,
                "analytics_supported": True,
            },
            [
                CameraProbeResult(
                    manufacturer="Axis",
                    model="P",
                    rtsp_url="rtsp://camera/stream",
                    onvif_port=80,
                    profile_token="profile-1",
                    profile_name="Main",
                    encoding="H264",
                    snapshot_uri="http://camera/snapshot",
                )
            ],
        )

        self.assertTrue(result["profile_s_likely"])
        self.assertTrue(result["profile_t_likely"])
        self.assertFalse(result["profile_g_likely"])
        self.assertTrue(result["profile_m_likely"])
        self.assertTrue(result["event_subscription_likely"])
        self.assertTrue(result["snapshot_supported"])
        self.assertTrue(result["h264_or_h265_supported"])

    def test_infers_missing_event_subscription_when_events_service_absent(self):
        result = ONVIFProbeService.infer_profile_compatibility(
            {"media_supported": True, "events_supported": False, "analytics_supported": False},
            [
                CameraProbeResult(
                    manufacturer="Legacy",
                    model="L",
                    rtsp_url="rtsp://camera/stream",
                    onvif_port=80,
                    profile_token="profile-1",
                    profile_name="Main",
                    encoding="MJPEG",
                )
            ],
        )

        self.assertTrue(result["profile_s_likely"])
        self.assertFalse(result["profile_t_likely"])
        self.assertFalse(result["profile_m_likely"])
        self.assertFalse(result["event_subscription_likely"])
        self.assertIn("Events servisi gorunmedi", " ".join(result["compatibility_notes"]))


if __name__ == "__main__":
    unittest.main()
