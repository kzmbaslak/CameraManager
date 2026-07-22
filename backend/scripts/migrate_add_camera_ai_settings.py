"""Mevcut SQLite veritabanina kamera bazli AI ayarlari kolonlarini ekler."""

from __future__ import annotations

import os
import sqlite3


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "nvr_system.db"))


COLUMNS = {
    "ai_confidence_threshold": "REAL DEFAULT 0.5",
    "ai_iou_threshold": "REAL DEFAULT 0.45",
    "ai_alarm_cooldown_seconds": "INTEGER DEFAULT 60",
    "ai_frame_stride": "INTEGER DEFAULT 1",
    "ai_inference_width": "INTEGER DEFAULT 640",
    "ai_active_start": "TEXT",
    "ai_active_end": "TEXT",
    "ai_roi_polygon": "TEXT",
}


def main() -> None:
    """Eksik kolonlari idempotent bicimde ekler."""
    if not os.path.exists(DB_PATH):
        print(f"Veritabani bulunamadi: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(cameras)").fetchall()}
        for column, definition in COLUMNS.items():
            if column in existing:
                print(f"Var: cameras.{column}")
                continue
            conn.execute(f"ALTER TABLE cameras ADD COLUMN {column} {definition}")
            print(f"Eklendi: cameras.{column}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
