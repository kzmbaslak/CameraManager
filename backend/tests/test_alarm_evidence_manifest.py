import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.presentation.api.routes.alarms import _evidence_file_item


class AlarmEvidenceManifestTests(unittest.TestCase):
    def test_missing_snapshot_is_reported_without_path(self):
        item = _evidence_file_item("raw", None, None)

        self.assertFalse(item.available)
        self.assertEqual(item.status, "not_recorded")
        self.assertIsNone(item.filename)

    def test_hash_and_size_are_reported_for_safe_snapshot(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                snapshot_dir = Path("snapshots")
                snapshot_dir.mkdir()
                snapshot_path = snapshot_dir / "alarm.jpg"
                snapshot_path.write_bytes(b"evidence")

                item = _evidence_file_item("raw", str(snapshot_path), None)
            finally:
                os.chdir(previous_cwd)

        self.assertTrue(item.available)
        self.assertEqual(item.filename, "alarm.jpg")
        self.assertEqual(item.size_bytes, 8)
        self.assertEqual(item.status, "ok")
        self.assertEqual(len(item.sha256 or ""), 64)

    def test_unsafe_snapshot_path_does_not_return_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                Path("snapshots").mkdir()
                outside_path = Path(tmp).parent / "outside-alarm.jpg"
                item = _evidence_file_item("raw", str(outside_path), None)
            finally:
                os.chdir(previous_cwd)

        self.assertFalse(item.available)
        self.assertEqual(item.status, "unsafe_path")
        self.assertIsNone(item.sha256)

    def test_hash_mismatch_is_marked_for_recalculation(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_cwd = os.getcwd()
            try:
                os.chdir(tmp)
                snapshot_dir = Path("snapshots")
                snapshot_dir.mkdir()
                snapshot_path = snapshot_dir / "alarm.jpg"
                snapshot_path.write_bytes(b"changed")

                item = _evidence_file_item("annotated", str(snapshot_path), "bad")
            finally:
                os.chdir(previous_cwd)

        self.assertTrue(item.available)
        self.assertEqual(item.status, "hash_mismatch_recalculated")


if __name__ == "__main__":
    unittest.main()
