"""Mevcut SQLite veritabanina kamera saglik gecmisi tablosunu ekler."""

from __future__ import annotations

import os
import sqlite3


DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "nvr_system.db"))


def main() -> None:
    """Kamera saglik gecmisi tablosunu idempotent bicimde olusturur."""
    if not os.path.exists(DB_PATH):
        print(f"Veritabani bulunamadi: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS camera_health_samples (
                id INTEGER PRIMARY KEY,
                camera_id INTEGER,
                checked_at DATETIME,
                reachable BOOLEAN DEFAULT 0,
                status TEXT DEFAULT 'unknown',
                latency_ms REAL,
                failure_reason TEXT,
                FOREIGN KEY(camera_id) REFERENCES cameras(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS ix_camera_health_samples_camera_id ON camera_health_samples(camera_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS ix_camera_health_samples_checked_at ON camera_health_samples(checked_at)")
        conn.commit()
        print("Hazir: camera_health_samples")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
