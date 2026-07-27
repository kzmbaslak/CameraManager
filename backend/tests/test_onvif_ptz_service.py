import unittest

from src.infrastructure.onvif.onvif_probe_service import ONVIFProbeService


class _FakeMedia:
    def GetProfiles(self):
        return {"Profiles": [{"token": "profile-1"}]}


class _FakePtz:
    def __init__(self):
        self.home_request = None

    def GetPresets(self, request):
        return {
            "Preset": [
                {"token": "preset-1", "Name": "Gate"},
                {"@token": "preset-2", "Name": "Yard"},
            ]
        }

    def GotoHomePosition(self, request):
        self.home_request = request


class _FakeCamera:
    def __init__(self):
        self.ptz = _FakePtz()

    def create_media_service(self):
        return _FakeMedia()

    def create_ptz_service(self):
        return self.ptz


class _FakePtzService(ONVIFProbeService):
    def __init__(self):
        self.camera = _FakeCamera()

    def _connect(self, host, port, username, password):
        return self.camera


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

    def test_preset_list_uses_profile_token_without_credentials_in_result(self):
        presets = _FakePtzService().get_ptz_presets("10.0.0.10", 80, "operator", "secret")

        self.assertEqual(len(presets), 2)
        self.assertEqual(presets[0]["token"], "preset-1")
        self.assertEqual(presets[0]["name"], "Gate")
        self.assertEqual(presets[0]["profile_token"], "profile-1")
        self.assertNotIn("secret", str(presets))

    def test_goto_home_uses_profile_token_without_credentials_in_result(self):
        service = _FakePtzService()
        result = service.goto_ptz_home("10.0.0.10", 80, "operator", "secret")

        self.assertEqual(result["profile_token"], "profile-1")
        self.assertEqual(service.camera.ptz.home_request, {"ProfileToken": "profile-1"})
        self.assertNotIn("secret", str(result))


if __name__ == "__main__":
    unittest.main()
