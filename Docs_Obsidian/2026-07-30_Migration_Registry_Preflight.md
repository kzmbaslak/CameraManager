# 2026-07-30 Migration Registry Preflight

- Preflight migration kontrolu dosya varligiyla sinirli kalmaz; sirali registry uzerinden dosya, entrypoint ve hedef tablo/kolon sinyallerini denetler.
- `MIGRATION_REGISTRY` her scriptin hangi sema degisimini kapsadigini acik hale getirir.
- `backend/tests/test_setup_preflight.py` eksik dosya, eksik entrypoint ve registry benzersizlik/sira kontratini korur.
