"""Yedek arşivini doğrular ve onayla sistem verilerini geri yükler."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_RECORDING_DIR = BACKEND_DIR / "data" / "recordings"
RESTORABLE_PREFIXES = ("data/", "models/", "snapshots/", "recordings/")
RESTORABLE_FILES = {".env"}
RESTORE_CONFIRMATION_PHRASE = "RESTORE_OVERWRITE_CONFIRMED"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _is_restorable(path: str) -> bool:
    return path in RESTORABLE_FILES or any(path.startswith(prefix) for prefix in RESTORABLE_PREFIXES)


def _recording_storage_dir() -> Path:
    return Path(os.environ.get("RECORDING_STORAGE_DIR", str(DEFAULT_RECORDING_DIR))).resolve()


def _safe_target(path: str) -> Path:
    if not _is_restorable(path):
        raise ValueError(f"Arsiv yolu geri yukleme kapsaminda degil: {path}")
    if path.startswith("recordings/"):
        target = (_recording_storage_dir() / path.removeprefix("recordings/")).resolve()
        recording_root = _recording_storage_dir()
        if recording_root not in target.parents and target != recording_root:
            raise ValueError(f"Arsiv yolu guvenli degil: {path}")
        return target
    target = (BACKEND_DIR / path).resolve()
    if BACKEND_DIR not in target.parents and target != BACKEND_DIR:
        raise ValueError(f"Arsiv yolu guvenli degil: {path}")
    return target


def _load_manifest(archive: zipfile.ZipFile) -> dict:
    try:
        with archive.open("manifest.json") as file:
            manifest = json.loads(file.read().decode("utf-8"))
    except KeyError as exc:
        raise ValueError("manifest.json bulunamadi.") from exc
    if not isinstance(manifest.get("files"), list):
        raise ValueError("manifest.json dosya listesi gecersiz.")
    return manifest


def _extract_and_verify(backup_path: Path, temp_root: Path) -> list[tuple[Path, Path]]:
    restore_items: list[tuple[Path, Path]] = []
    with zipfile.ZipFile(backup_path, "r") as archive:
        manifest = _load_manifest(archive)
        for item in manifest["files"]:
            rel_path = item.get("path")
            expected_sha256 = item.get("sha256")
            if not isinstance(rel_path, str) or not isinstance(expected_sha256, str):
                raise ValueError("Manifest dosya girdisi gecersiz.")
            target = _safe_target(rel_path)
            extracted = (temp_root / rel_path).resolve()
            if temp_root not in extracted.parents:
                raise ValueError(f"Arsiv yolu guvenli degil: {rel_path}")
            archive.extract(rel_path, temp_root)
            actual_sha256 = _sha256(extracted)
            if actual_sha256 != expected_sha256:
                raise ValueError(f"SHA-256 dogrulamasi basarisiz: {rel_path}")
            restore_items.append((extracted, target))
    return restore_items


def restore_backup(
    backup_path: Path,
    force: bool = False,
    dry_run: bool = False,
    confirmation: str | None = None,
) -> list[str]:
    """Yedeği doğrular, force verilirse dosyaları geri yükler."""
    if not backup_path.is_file():
        raise FileNotFoundError(f"Yedek bulunamadi: {backup_path}")
    with tempfile.TemporaryDirectory() as temp_dir:
        restore_items = _extract_and_verify(backup_path, Path(temp_dir).resolve())
        restored_paths = [str(target) for _, target in restore_items]
        if dry_run:
            return restored_paths
        if not force:
            raise RuntimeError("Geri yukleme dosya yazar; devam etmek icin --force kullanin.")
        if confirmation != RESTORE_CONFIRMATION_PHRASE:
            raise RuntimeError(
                "Geri yukleme mevcut dosyalarin ustune yazar; devam etmek icin "
                f"--confirm-restore {RESTORE_CONFIRMATION_PHRASE} kullanin."
            )
        for source, target in restore_items:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
        return restored_paths


def main() -> None:
    parser = argparse.ArgumentParser(description="Kamera yonetimi sistem yedegini geri yukler.")
    parser.add_argument("backup", type=Path, help="Yedek zip dosyasi.")
    parser.add_argument("--force", action="store_true", help="Dogrulanan dosyalari hedefe yaz.")
    parser.add_argument("--dry-run", action="store_true", help="Sadece arsivi dogrula ve yazilacak dosyalari listele.")
    parser.add_argument(
        "--confirm-restore",
        default=None,
        help=f"Yazma islemi icin ikinci onay metni: {RESTORE_CONFIRMATION_PHRASE}",
    )
    args = parser.parse_args()
    restored = restore_backup(args.backup, force=args.force, dry_run=args.dry_run, confirmation=args.confirm_restore)
    action = "Dogrulandi" if args.dry_run or not args.force else "Geri yuklendi"
    print(f"{action}: {len(restored)} dosya")
    for path in restored:
        print(path)


if __name__ == "__main__":
    main()
