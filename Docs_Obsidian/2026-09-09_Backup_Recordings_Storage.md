# 2026-09-09 Backup Recordings Storage

- Backup sistemi `RECORDING_STORAGE_DIR` varsayilan `backend/data/recordings` disina tasindiginda kayit dosyalarini artik `recordings/` arsiv prefix'i altinda manifestli olarak yedekler.
- Restore script'i `recordings/` prefix'ini mevcut `RECORDING_STORAGE_DIR` hedefine acar ve path traversal denemesini kayit kok dizini sinirinda reddeder.
- Restore yazma islemi icin `--force` yaninda `--confirm-restore RESTORE_OVERWRITE_CONFIRMED` gerekir; `--dry-run` bu onay olmadan sadece dogrulama yapabilir.
- `backend/tests/test_system_backup.py` dis kayit storage arsivleme davranisini ve restore hedef cozumlemesini korur.
