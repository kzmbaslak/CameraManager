import unittest

from src.infrastructure.onvif.onvif_probe_service import ONVIFProbeService


class OnvifPtzServiceTests(unittest.TestCase):
    def test_pan_tilt_velocity_is_clamped_and_mapped(self):
        velocity = ONVIFProbeService._ptz_velocity("up_right", 2.5)

        self.assertEqual(velocity["PanTilt"], {"x": 1.0, "y": 1.0})
        self.assertNotIn("Zoom", velocity)

    def test_zoom_velocity_is_mapped(self):
        velocity = ONVIFProbeService._ptz_velocity("zoom_out", 0.4)

        self.assertEqual(velocity["Zoom"], {"x": -0.4})
        self.assertNotIn("PanTilt", velocity)

    def test_invalid_direction_is_rejected(self):
        with self.assertRaises(ValueError):
            ONVIFProbeService._ptz_velocity("home", 0.5)


if __name__ == "__main__":
    unittest.main()
