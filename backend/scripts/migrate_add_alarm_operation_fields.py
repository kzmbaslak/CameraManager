"""Mevcut SQLite veritabanina alarm operasyon kolonlarini ekler."""

from __future__ import annotations

import os
import sqlite3
import hashlib


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "nvr_system.db"))
COLUMNS = {
    "assigned_to": "TEXT",
    "operator_note": "TEXT",
    "resolution_reason": "TEXT",
    "severity": "TEXT DEFAULT 'medium'",
    "false_positive": "BOOLEAN DEFAULT 0",
    "snapshot_sha256": "TEXT",
}


def backfill_snapshot_hashes(conn: sqlite3.Connection) -> None:
    """Mevcut snapshot dosyalari icin eksik SHA-256 degerlerini doldurur."""
    rows = conn.execute(
        "SELECT id, snapshot_path FROM alarms WHERE snapshot_path IS NOT NULL AND snapshot_sha256 IS NULL"
    ).fetchall()
    for alarm_id, snapshot_path in rows:
        if not snapshot_path:
            continue
        absolute_path = os.path.abspath(snapshot_path)
        if not os.path.isfile(absolute_path):
            print(f"Atlandi: Alarm #{alarm_id} snapshot dosyasi yok")
            continue
        with open(absolute_path, "rb") as file:
            snapshot_sha256 = hashlib.sha256(file.read()).hexdigest()
        conn.execute(
            "UPDATE alarms SET snapshot_sha256 = ? WHERE id = ?",
            (snapshot_sha256, alarm_id),
        )
        print(f"Guncellendi: Alarm #{alarm_id} snapshot_sha256")


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
        backfill_snapshot_hashes(conn)
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
