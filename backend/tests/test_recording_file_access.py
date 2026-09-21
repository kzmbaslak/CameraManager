"""Recording file access guvenlik siniri testleri."""

import tempfile
import unittest
import os
from datetime import timedelta
from pathlib import Path

os.environ.setdefault("CAMERA_ENCRYPTION_KEY", "MDEyMzQ1Njc4OWFiY2RlZjAxMjM0NTY3ODlhYmNkZWY=")
os.environ.setdefault("JWT_SECRET_KEY", "0123456789abcdef0123456789abcdef")

from fastapi import HTTPException, status

from src.domain.entities.recording_segment import RecordingSegment
from src.presentation.api.routes.recordings import _recording_metadata_response, _safe_recording_file_path
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

    def test_recording_metadata_reads_detection_sidecar_without_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = root / "event.mp4"
            path.write_bytes(b"mp4")
            path.with_suffix(".detections.json").write_text(
                '{"frame_width":48,"frame_height":32,"detected_at":"2026-07-28T10:00:00Z",'
                '"detections":[{"label":"person","confidence":0.92,'
                '"bounding_box":{"x":5,"y":6,"width":12,"height":18}}]}',
                encoding="utf-8",
            )

            metadata = _recording_metadata_response(self._segment(path), root)

            self.assertEqual(metadata.frame_width, 48)
            self.assertEqual(metadata.frame_height, 32)
            self.assertEqual(len(metadata.detections), 1)
            self.assertEqual(metadata.detections[0].bounding_box.x, 5)

    def test_recording_metadata_reads_motion_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = root / "motion.mp4"
            path.write_bytes(b"mp4")
            path.with_suffix(".detections.json").write_text(
                '{"frame_width":160,"frame_height":120,"detected_at":"2026-09-21T10:00:00Z",'
                '"detections":[],"motion":{"changed_ratio":0.1875,"changed_percent":18.75}}',
                encoding="utf-8",
            )

            metadata = _recording_metadata_response(self._segment(path), root)

            self.assertEqual(metadata.detections, [])
            self.assertIsNotNone(metadata.motion)
            self.assertEqual(metadata.motion.changed_ratio, 0.1875)
            self.assertEqual(metadata.motion.changed_percent, 18.75)

    def test_recording_metadata_returns_empty_when_sidecar_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            path = root / "event.mp4"
            path.write_bytes(b"mp4")

            metadata = _recording_metadata_response(self._segment(path), root)

            self.assertEqual(metadata.detections, [])
            self.assertEqual(metadata.frame_width, None)
            self.assertIsNone(metadata.motion)


if __name__ == "__main__":
    unittest.main()
