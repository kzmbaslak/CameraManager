# 2026-07-29 Camera Bulk AI Profile

- Kamera listesinde yetkili kullanici gorunen kameralari secerek toplu AI profili uygulayabilir.
- Hassas, Dengeli ve Siki profilleri secili kameralara tek islemle yazilir.
- Backend `camera.bulk_ai_settings` audit olayi uretir ve her kamera icin stream state yenilenir.
- Dinamik kamera rotalari `camera_id:int` ile sinirlandirildi; statik rotalarin kamera ID rotasi tarafindan golgelenmesi engellendi.
