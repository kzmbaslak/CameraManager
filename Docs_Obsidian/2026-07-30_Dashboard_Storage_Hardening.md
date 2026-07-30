# 2026-07-30 Dashboard Storage Hardening

- Canli izleme kamera siralama tercihi localStorage'dan okunurken pozitif integer ID, tekrar temizleme ve maksimum uzunluk kontrolunden gecer.
- Kaydedilen kamera sirasi da ayni sanitizer ile yazilir.
- Contract testi dashboard kamera sirasi storage limitinin ve sanitizer'in korunmasini denetler.
