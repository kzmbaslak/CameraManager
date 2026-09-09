# 2026-09-09 Backup Recordings Storage

- Backup sistemi `RECORDING_STORAGE_DIR` varsayilan `backend/data/recordings` disina tasindiginda kayit dosyalarini artik `recordings/` arsiv prefix'i altinda manifestli olarak yedekler.
- Restore script'i `recordings/` prefix'ini mevcut `RECORDING_STORAGE_DIR` hedefine acar ve path traversal denemesini kayit kok dizini sinirinda reddeder.
- `backend/tests/test_system_backup.py` dis kayit storage arsivleme davranisini ve restore hedef cozumlemesini korur.
