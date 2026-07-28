"""Recording file access guvenlik siniri testleri."""

import tempfile
import unittest
from datetime import timedelta
from pathlib import Path

from fastapi import HTTPException, status

from src.domain.entities.recording_segment import RecordingSegment
from src.presentation.api.routes.recordings import _safe_recording_file_path
from src.infrastructure.time_utils import utc_now


class RecordingFileAccessTests(unittest.TestCase):
    def _segment(self, file_path: Path, *, status_value: str = "complete") -> RecordingSegment:
        now = utc_now()
        return RecordingSegment(
            id=12,
            camera_id=3,
            started_at=now - timedelta(seconds=8),
            ended_at=now,
            recording_type="event",
            status=status_value,
            file_path=str(file_path),
            file_sha256="abc",
            size_bytes=3,
        )

    def test_safe_recording_file_path_allows_completed_file_inside_storage(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = root / "cam-3-event.mp4"
            path.write_bytes(b"mp4")

            resolved = _safe_recording_file_path(self._segment(path), root)

            self.assertEqual(resolved, path)

    def test_safe_recording_file_path_rejects_file_outside_storage(self):
        with tempfile.TemporaryDirectory() as root_tmp, tempfile.TemporaryDirectory() as outside_tmp:
            outside_path = Path(outside_tmp).resolve() / "leak.mp4"
            outside_path.write_bytes(b"mp4")

            with self.assertRaises(HTTPException) as ctx:
                _safe_recording_file_path(self._segment(outside_path), Path(root_tmp))

            self.assertEqual(ctx.exception.status_code, status.HTTP_403_FORBIDDEN)

    def test_safe_recording_file_path_rejects_open_segment(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = root / "open.mp4"
            path.write_bytes(b"mp4")
            segment = self._segment(path, status_value="recording")
            segment.ended_at = None

            with self.assertRaises(HTTPException) as ctx:
                _safe_recording_file_path(segment, root)

            self.assertEqual(ctx.exception.status_code, status.HTTP_409_CONFLICT)

    def test_safe_recording_file_path_rejects_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()

            with self.assertRaises(HTTPException) as ctx:
                _safe_recording_file_path(self._segment(root / "missing.mp4"), root)

            self.assertEqual(ctx.exception.status_code, status.HTTP_404_NOT_FOUND)


if __name__ == "__main__":
    unittest.main()
