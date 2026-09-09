"""Sistem yedegi kayit dosyasi kapsami testleri."""

from __future__ import annotations

import importlib.util
import os
import sqlite3
import tempfile
import unittest
import zipfile
from pathlib import Path

from src.infrastructure.backup import system_backup


def _load_restore_module():
    path = Path(__file__).resolve().parents[1] / "scripts" / "restore_system.py"
    spec = importlib.util.spec_from_file_location("restore_system_for_test", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("restore_system.py yuklenemedi")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SystemBackupRecordingTests(unittest.TestCase):
    def setUp(self):
        self._env_backup = os.environ.get("RECORDING_STORAGE_DIR")

    def tearDown(self):
        if self._env_backup is None:
            os.environ.pop("RECORDING_STORAGE_DIR", None)
        else:
            os.environ["RECORDING_STORAGE_DIR"] = self._env_backup

    def test_external_recording_storage_is_archived_under_recordings_prefix(self):
        with tempfile.TemporaryDirectory() as backend_tmp, tempfile.TemporaryDirectory() as recording_tmp:
            backend_root = Path(backend_tmp)
            recording_root = Path(recording_tmp)
            db_path = backend_root / "data" / "nvr_system.db"
            db_path.parent.mkdir(parents=True)
            sqlite3.connect(db_path).close()
            video_path = recording_root / "cam_1" / "event.mp4"
            video_path.parent.mkdir(parents=True)
            video_path.write_bytes(b"video")
            os.environ["RECORDING_STORAGE_DIR"] = str(recording_root)

            old_backend_dir = system_backup.BACKEND_DIR
            old_default_output_dir = system_backup.DEFAULT_OUTPUT_DIR
            old_db_path = system_backup.DB_PATH
            old_default_recording_dir = system_backup.DEFAULT_RECORDING_DIR
            old_include_paths = system_backup.INCLUDE_PATHS
            try:
                system_backup.BACKEND_DIR = backend_root
                system_backup.DEFAULT_OUTPUT_DIR = backend_root / "backups"
                system_backup.DB_PATH = db_path
                system_backup.DEFAULT_RECORDING_DIR = backend_root / "data" / "recordings"
                system_backup.INCLUDE_PATHS = [backend_root / ".env", backend_root / "data"]
                backup_path = system_backup.create_backup(backend_root / "backup.zip")
            finally:
                system_backup.BACKEND_DIR = old_backend_dir
                system_backup.DEFAULT_OUTPUT_DIR = old_default_output_dir
                system_backup.DB_PATH = old_db_path
                system_backup.DEFAULT_RECORDING_DIR = old_default_recording_dir
                system_backup.INCLUDE_PATHS = old_include_paths

            with zipfile.ZipFile(backup_path) as archive:
                names = set(archive.namelist())
                self.assertIn("data/nvr_system.db", names)
                self.assertIn("recordings/cam_1/event.mp4", names)
                self.assertIn("manifest.json", names)

    def test_restore_recordings_prefix_targets_configured_recording_storage(self):
        restore_system = _load_restore_module()
        with tempfile.TemporaryDirectory() as backend_tmp, tempfile.TemporaryDirectory() as recording_tmp:
            backend_root = Path(backend_tmp)
            recording_root = Path(recording_tmp)
            os.environ["RECORDING_STORAGE_DIR"] = str(recording_root)
            old_backend_dir = restore_system.BACKEND_DIR
            old_default_recording_dir = restore_system.DEFAULT_RECORDING_DIR
            try:
                restore_system.BACKEND_DIR = backend_root
                restore_system.DEFAULT_RECORDING_DIR = backend_root / "data" / "recordings"
                target = restore_system._safe_target("recordings/cam_1/event.mp4")
            finally:
                restore_system.BACKEND_DIR = old_backend_dir
                restore_system.DEFAULT_RECORDING_DIR = old_default_recording_dir

            self.assertEqual(target, recording_root / "cam_1" / "event.mp4")


if __name__ == "__main__":
    unittest.main()
