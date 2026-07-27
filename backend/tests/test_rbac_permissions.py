"""RBAC izin matrisi regresyon testleri."""

import os
import unittest

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.presentation.api.dependencies import get_role_permissions


class RbacPermissionTests(unittest.TestCase):
    def test_admin_has_all_named_permissions(self):
        permissions = get_role_permissions("admin")

        self.assertTrue({
            "audit.read",
            "backup.manage",
            "camera.diagnostics",
            "camera.manage",
            "evidence.export",
            "live.view",
            "nvr.manage",
            "ptz.control",
            "recording.manage",
            "recording.view",
            "security.status",
            "user.manage",
            "alarm.operate",
        }.issubset(permissions))

    def test_operator_can_apply_thresholds_but_not_manage_users(self):
        permissions = get_role_permissions("operator")

        self.assertIn("camera.manage", permissions)
        self.assertIn("evidence.export", permissions)
        self.assertIn("alarm.operate", permissions)
        self.assertIn("ptz.control", permissions)
        self.assertIn("recording.view", permissions)
        self.assertNotIn("recording.manage", permissions)
        self.assertNotIn("user.manage", permissions)
        self.assertNotIn("audit.read", permissions)
        self.assertNotIn("backup.manage", permissions)

    def test_viewer_is_live_view_only(self):
        self.assertEqual(get_role_permissions("viewer"), {"live.view"})

    def test_unknown_role_has_no_permissions(self):
        self.assertEqual(get_role_permissions(""), set())
        self.assertEqual(get_role_permissions(None), set())


if __name__ == "__main__":
    unittest.main()
