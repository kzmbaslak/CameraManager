"""Create verified system backup archives with a manifest."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime, timedelta
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[3]
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "backups"
BACKUP_FILE_PATTERN = "kamera-backup-*.zip"
DB_PATH = BACKEND_DIR / "data" / "nvr_system.db"
DEFAULT_RECORDING_DIR = BACKEND_DIR / "data" / "recordings"
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


def external_archive_dir() -> Path | None:
    """Opsiyonel kurumsal dis arsiv dizinini cozer."""
    raw_path = os.environ.get("BACKUP_EXTERNAL_ARCHIVE_DIR", "").strip()
    return Path(raw_path).expanduser().resolve() if raw_path else None


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


def _recording_storage_dir() -> Path:
    """Kayit kok dizinini backup icin env veya varsayilandan cozer."""
    return Path(os.environ.get("RECORDING_STORAGE_DIR", str(DEFAULT_RECORDING_DIR))).resolve()


def _is_within(path: Path, root: Path) -> bool:
    return path == root or root in path.parents


def _is_covered_by_static_include(path: Path) -> bool:
    for include_path in INCLUDE_PATHS:
        resolved = include_path.resolve()
        if _is_within(path, resolved):
            return True
    return False


def _backup_entries(files: list[Path]) -> list[tuple[Path, str]]:
    entries: dict[str, Path] = {}
    for file_path in files:
        if file_path == DB_PATH:
            continue
        if file_path.name == "nvr_system.db" and file_path.parent.name == "data" and not _is_within(file_path, BACKEND_DIR):
            entries["data/nvr_system.db"] = file_path
            continue
        if _is_within(file_path, BACKEND_DIR):
            arcname = file_path.relative_to(BACKEND_DIR).as_posix()
        else:
            continue
        entries[arcname] = file_path

    recording_root = _recording_storage_dir()
    if recording_root.exists() and not _is_covered_by_static_include(recording_root):
        for file_path in _iter_files([recording_root]):
            relative = file_path.relative_to(recording_root).as_posix()
            entries[f"recordings/{relative}"] = file_path

    return [(path, arcname) for arcname, path in sorted(entries.items())]


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


def mirror_backup_to_external_archive(backup_path: Path, archive_dir: Path | None = None) -> Path | None:
    """Yedegi opsiyonel dis arsiv dizinine kopyalar ve SHA-256 sidecar yazar."""
    target_dir = archive_dir or external_archive_dir()
    if target_dir is None:
        return None
    resolved_backup = backup_path.resolve()
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = (target_dir / backup_path.name).resolve()
    if target_path == resolved_backup:
        digest = _sha256(resolved_backup)
        target_path.with_suffix(target_path.suffix + ".sha256").write_text(
            f"{digest}  {target_path.name}\n",
            encoding="utf-8",
        )
        return target_path
    if target_dir not in target_path.parents and target_path != target_dir:
        raise ValueError("Dis arsiv hedefi guvenli degil.")
    shutil.copy2(resolved_backup, target_path)
    digest = _sha256(target_path)
    target_path.with_suffix(target_path.suffix + ".sha256").write_text(
        f"{digest}  {target_path.name}\n",
        encoding="utf-8",
    )
    return target_path


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
            for file_path, arcname in _backup_entries(files):
                archive.write(file_path, arcname)
                manifest["files"].append({
                    "path": arcname,
                    "sha256": _sha256(file_path),
                    "size": file_path.stat().st_size,
                })
            archive.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    mirror_backup_to_external_archive(output_path)
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
