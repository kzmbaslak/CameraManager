"""Mevcut SQLite veritabanina alarm operasyon kolonlarini ekler."""

from __future__ import annotations

import os
import sqlite3


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "nvr_system.db"))
COLUMNS = {
    "assigned_to": "TEXT",
    "operator_note": "TEXT",
    "resolution_reason": "TEXT",
    "severity": "TEXT DEFAULT 'medium'",
    "false_positive": "BOOLEAN DEFAULT 0",
}


def main() -> None:
    """Eksik alarm operasyon kolonlarini idempotent bicimde ekler."""
    if not os.path.exists(DB_PATH):
        print(f"Veritabani bulunamadi: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        existing = {row[1] for row in conn.execute("PRAGMA table_info(alarms)").fetchall()}
        for column, definition in COLUMNS.items():
            if column in existing:
                print(f"Var: alarms.{column}")
                continue
            conn.execute(f"ALTER TABLE alarms ADD COLUMN {column} {definition}")
            print(f"Eklendi: alarms.{column}")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
