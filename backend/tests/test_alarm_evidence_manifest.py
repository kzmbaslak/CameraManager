import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from src.presentation.api.routes.alarms import _evidence_file_item
from src.presentation.api.routes.alarms import _recording_evidence_file_items
from src.domain.entities.recording_segment import RecordingSegment
from src.infrastructure.time_utils import utc_now


class FakeRecordingRepository:
    def __init__(self, segments):
        self._segments = segments

    def list_by_alarm_id(self, alarm_id: int):
        return [segment for segment in self._segments if segment.alarm_id == alarm_id]


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

    def test_recording_video_is_reported_without_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_storage = os.environ.get("RECORDING_STORAGE_DIR")
            try:
                os.environ["RECORDING_STORAGE_DIR"] = tmp
                video_path = Path(tmp) / "event.mp4"
                video_path.write_bytes(b"video")
                segment = RecordingSegment(
                    id=1,
                    camera_id=2,
                    started_at=utc_now(),
                    ended_at=utc_now(),
                    recording_type="event",
                    status="complete",
                    file_path=str(video_path),
                    file_sha256=None,
                    size_bytes=5,
                    alarm_id=99,
                )

                items = _recording_evidence_file_items(99, FakeRecordingRepository([segment]))
            finally:
                if previous_storage is None:
                    os.environ.pop("RECORDING_STORAGE_DIR", None)
                else:
                    os.environ["RECORDING_STORAGE_DIR"] = previous_storage

        self.assertEqual(len(items), 1)
        self.assertTrue(items[0].available)
        self.assertEqual(items[0].variant, "video_event_1")
        self.assertEqual(items[0].filename, "event.mp4")
        self.assertEqual(items[0].size_bytes, 5)
        self.assertEqual(items[0].status, "ok")
        self.assertEqual(len(items[0].sha256 or ""), 64)

    def test_recording_video_outside_storage_is_rejected(self):
        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as outside_tmp:
            previous_storage = os.environ.get("RECORDING_STORAGE_DIR")
            try:
                os.environ["RECORDING_STORAGE_DIR"] = root_tmp
                segment = RecordingSegment(
                    id=2,
                    camera_id=2,
                    started_at=utc_now(),
                    ended_at=utc_now(),
                    recording_type="event",
                    status="complete",
                    file_path=str(Path(outside_tmp) / "outside.mp4"),
                    alarm_id=99,
                )

                items = _recording_evidence_file_items(99, FakeRecordingRepository([segment]))
            finally:
                if previous_storage is None:
                    os.environ.pop("RECORDING_STORAGE_DIR", None)
                else:
                    os.environ["RECORDING_STORAGE_DIR"] = previous_storage

        self.assertFalse(items[0].available)
        self.assertEqual(items[0].status, "unsafe_path")
        self.assertIsNone(items[0].filename)

    def test_recording_video_open_segment_is_not_available(self):
        with tempfile.TemporaryDirectory() as tmp:
            previous_storage = os.environ.get("RECORDING_STORAGE_DIR")
            try:
                os.environ["RECORDING_STORAGE_DIR"] = tmp
                video_path = Path(tmp) / "open.mp4"
                video_path.write_bytes(b"video")
                segment = RecordingSegment(
                    id=3,
                    camera_id=2,
                    started_at=utc_now(),
                    ended_at=None,
                    recording_type="event",
                    status="recording",
                    file_path=str(video_path),
                    file_sha256="known",
                    size_bytes=5,
                    alarm_id=99,
                )

                items = _recording_evidence_file_items(99, FakeRecordingRepository([segment]))
            finally:
                if previous_storage is None:
                    os.environ.pop("RECORDING_STORAGE_DIR", None)
                else:
                    os.environ["RECORDING_STORAGE_DIR"] = previous_storage

        self.assertFalse(items[0].available)
        self.assertEqual(items[0].filename, "open.mp4")
        self.assertEqual(items[0].status, "not_complete")


if __name__ == "__main__":
    unittest.main()
