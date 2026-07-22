"""Sistem verilerini manifest ve SHA-256 ile yedek arşivine alır."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
import tempfile
import zipfile
from datetime import UTC, datetime
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT_DIR = BACKEND_DIR / "backups"
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
    """Yedek zip dosyasını oluşturur ve dosya yolunu döndürür."""
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Kamera yonetimi sistem yedegi olusturur.")
    parser.add_argument("--output", type=Path, help="Yedek zip dosyasi yolu.")
    args = parser.parse_args()
    backup_path = create_backup(args.output)
    print(f"Yedek olusturuldu: {backup_path}")


if __name__ == "__main__":
    main()
