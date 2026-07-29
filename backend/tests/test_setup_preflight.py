"""Setup preflight kontrolleri regresyon testleri."""

import unittest
from unittest.mock import patch

from src.infrastructure.setup import preflight


class SetupPreflightTests(unittest.TestCase):
    def test_required_schema_includes_camera_recording_policy(self):
        self.assertIn("continuous_recording_enabled", preflight.REQUIRED_SCHEMA["cameras"])

    def test_migration_script_inventory_reports_missing_scripts(self):
        def fake_isfile(path: str) -> bool:
            return not path.endswith("migrate_add_camera_ai_settings.py")

        with patch.object(preflight.os.path, "isfile", side_effect=fake_isfile):
            result = preflight._migration_script_inventory_check()

        self.assertFalse(result.ok)
        self.assertEqual(result.key, "migration_script_inventory")
        self.assertEqual(result.severity, "medium")
        self.assertIn("migrate_add_camera_ai_settings.py", result.message)

    def test_migration_script_inventory_passes_when_all_scripts_exist(self):
        with patch.object(preflight.os.path, "isfile", return_value=True):
            result = preflight._migration_script_inventory_check()

        self.assertTrue(result.ok)
        self.assertEqual(result.key, "migration_script_inventory")


if __name__ == "__main__":
    unittest.main()
