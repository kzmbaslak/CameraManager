"""Create a verified system backup archive."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.infrastructure.backup.system_backup import create_backup


def main() -> None:
    parser = argparse.ArgumentParser(description="Kamera yonetimi sistem yedegi olusturur.")
    parser.add_argument("--output", type=Path, help="Yedek zip dosyasi yolu.")
    args = parser.parse_args()
    backup_path = create_backup(args.output)
    print(f"Yedek olusturuldu: {backup_path}")


if __name__ == "__main__":
    main()
