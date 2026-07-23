"""Create a verified system backup archive."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.infrastructure.backup.system_backup import DEFAULT_OUTPUT_DIR, cleanup_old_backups, create_backup


def _env_int(name: str, default: int) -> int:
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default
    try:
        return int(raw_value)
    except ValueError as exc:
        raise SystemExit(f"{name} sayisal olmali: {raw_value}") from exc


def main() -> None:
    parser = argparse.ArgumentParser(description="Kamera yonetimi sistem yedegi olusturur.")
    parser.add_argument("--output", type=Path, help="Yedek zip dosyasi yolu.")
    parser.add_argument(
        "--retention-days",
        type=int,
        default=_env_int("BACKUP_RETENTION_DAYS", 30),
        help="Otomatik uretilen yedeklerin saklanacagi gun sayisi.",
    )
    parser.add_argument(
        "--keep-latest",
        type=int,
        default=_env_int("BACKUP_KEEP_LATEST", 7),
        help="Retention suresi dolsa bile tutulacak en yeni yedek sayisi.",
    )
    parser.add_argument("--skip-cleanup", action="store_true", help="Eski yedek temizligini atla.")
    args = parser.parse_args()
    backup_path = create_backup(args.output)
    print(f"Yedek olusturuldu: {backup_path}")
    if not args.skip_cleanup:
        cleanup_dir = args.output.parent if args.output else DEFAULT_OUTPUT_DIR
        removed = cleanup_old_backups(cleanup_dir, args.retention_days, args.keep_latest)
        if removed:
            print(f"Eski yedek temizlendi: {len(removed)} dosya")
            for path in removed:
                print(path)


if __name__ == "__main__":
    main()
