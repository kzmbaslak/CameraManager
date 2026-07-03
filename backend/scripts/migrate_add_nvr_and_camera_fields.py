"""
Veritabanı migrasyon scripti — NVR tablosu ve kamera yeni alanları.

Mevcut nvr_system.db'ye şu değişiklikleri uygular:
  1. 'nvrs' tablosunu oluşturur (yoksa).
  2. 'cameras' tablosuna brand, model, nvr_id alanlarını ekler (yoksa).

Kullanım (backend/ klasöründe):
    venv\\Scripts\\python.exe scripts/migrate_add_nvr_and_camera_fields.py
"""
import os
import sqlite3

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "nvr_system.db")


def run():
    if not os.path.exists(DB_PATH):
        print(f"Veritabanı bulunamadı: {DB_PATH}")
        print("Uygulama bir kez başlatılarak tablo oluşturulabilir.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. nvrs tablosunu oluştur
    cur.execute("""
        CREATE TABLE IF NOT EXISTS nvrs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name VARCHAR NOT NULL,
            host VARCHAR NOT NULL,
            onvif_port INTEGER DEFAULT 80,
            username VARCHAR,
            encrypted_password VARCHAR,
            brand VARCHAR,
            model VARCHAR,
            is_active BOOLEAN DEFAULT 1,
            created_at DATETIME,
            updated_at DATETIME
        )
    """)
    print("nvrs tablosu: OK")

    # 2. cameras tablosuna yeni kolonları ekle
    columns_to_add = [
        ("brand",  "ALTER TABLE cameras ADD COLUMN brand VARCHAR"),
        ("model",  "ALTER TABLE cameras ADD COLUMN model VARCHAR"),
        ("nvr_id", "ALTER TABLE cameras ADD COLUMN nvr_id INTEGER REFERENCES nvrs(id)"),
    ]
    for col_name, sql in columns_to_add:
        try:
            cur.execute(sql)
            print(f"cameras.{col_name}: eklendi")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e):
                print(f"cameras.{col_name}: zaten mevcut, atlandı")
            else:
                raise

    conn.commit()
    conn.close()
    print("\nMigrasyon tamamlandı.")


if __name__ == "__main__":
    run()
