"""Create verified system backup archives with a manifest."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "backups"
BACKUP_FILE_PATTERN = "kamera-backup-*.zip"
DB_PATH = BACKEND_DIR / "data" / "nvr_system.db"
INCLUDE_PATHS = [
    BACKEND_DIR / ".env",
    BACKEND_DIR / "data",
    BACKEND_DIR / "models" / "yolov8n.onnx",
    BACKEND_DIR / "snapshots",
]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _iter_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if not path.exists():
            continue
        if path.is_dir():
            files.extend(item for item in path.rglob("*") if item.is_file())
        elif path.is_file():
            files.append(path)
    return sorted(set(files))


def _backup_sqlite(source: Path, target: Path) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        return
    source_conn = sqlite3.connect(str(source))
    target_conn = sqlite3.connect(str(target))
    try:
        source_conn.backup(target_conn)
    finally:
        target_conn.close()
        source_conn.close()


def create_backup(output: Path | None = None) -> Path:
    """Create a backup zip file and return its path."""
    DEFAULT_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    output_path = output or (DEFAULT_OUTPUT_DIR / f"kamera-backup-{timestamp}.zip")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_root = Path(temp_dir)
        db_copy = temp_root / "data" / "nvr_system.db"
        _backup_sqlite(DB_PATH, db_copy)
        files = _iter_files(INCLUDE_PATHS)
        if db_copy.exists():
            files.append(db_copy)

        manifest = {
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
            "version": 1,
            "files": [],
        }
        with zipfile.ZipFile(output_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for file_path in files:
                if file_path == DB_PATH:
                    continue
                if file_path == db_copy:
                    arcname = "data/nvr_system.db"
                else:
                    arcname = file_path.relative_to(BACKEND_DIR).as_posix()
                archive.write(file_path, arcname)
                manifest["files"].append({
                    "path": arcname,
                    "sha256": _sha256(file_path),
                    "size": file_path.stat().st_size,
                })
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    return output_path


def cleanup_old_backups(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    retention_days: int = 30,
    keep_latest: int = 7,
) -> list[Path]:
    """Delete old generated backup archives and return removed paths."""
    if retention_days < 1:
        raise ValueError("retention_days must be at least 1")
    if keep_latest < 1:
        raise ValueError("keep_latest must be at least 1")
    if not output_dir.exists():
        return []

    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    backups = sorted(
        (path for path in output_dir.glob(BACKUP_FILE_PATTERN) if path.is_file()),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    removable = backups[keep_latest:]
    removed: list[Path] = []
    for backup_path in removable:
        modified_at = datetime.fromtimestamp(backup_path.stat().st_mtime, UTC)
        if modified_at >= cutoff:
            continue
        backup_path.unlink()
        removed.append(backup_path)
    return removed
