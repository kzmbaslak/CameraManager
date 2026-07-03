# Scripts — Sistem Başlatma Dosyaları

## Hızlı Başlat

```cmd
scripts\run.bat
```

Geliştirme modu ile API sunucusu başlar. `http://127.0.0.1:8000` adresinde erişilebilir.

---

## Detaylı Seçenekler

### `run-dev.bat` — Geliştirme Modu
```cmd
scripts\run-dev.bat
```

- **Auto-reload:** Dosya değişikliğinde otomatik yeniden başlat
- **Tek işlem:** 1 worker
- **Hata mesajları:** Detaylı görüntülenir
- **Kullanım:** Aktif geliştirme sırasında

### `run-prod.bat` — Üretim Modu
```cmd
scripts\run-prod.bat
```

- **Yüksek performans:** 4 worker ile paralel işlem
- **Reload yok:** Daha hızlı başlama
- **Sabit:** Dosya değişiklikleri işlenir kapanmadan
- **Kullanım:** Production'da deploy etmek için

---

## API Endpoints

Sunucu başladıktan sonra:

- **Swagger UI:** `http://127.0.0.1:8000/docs` ← Tüm endpoint'leri interaktif test et
- **Health Check:** `http://127.0.0.1:8000/api/health`
- **ReDoc:** `http://127.0.0.1:8000/redoc`

---

## Sorun Giderme

### "venv klasoru bulunamadi" hatası
Önce `backend/` klasöründe venv oluştur:
```cmd
cd backend
python -m venv venv
venv\Scripts\pip.exe install -r requirements.txt
```

### Port 8000 zaten kullanılıyor
Başka bir port kullan (batch dosyalarını düzenle):
```cmd
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

---

## Gerekli Adımlar

**⚠️ Birinci başlatma öncesi:**

1. **YOLOv8 ONNX modelini yükle:** `backend/models/yolov8n.onnx` dosyasını yerleştir
   
2. **Test et:**
   ```cmd
   scripts\run.bat
   ```
   Sunucu başlarsa başarılı ✓

3. **Swagger UI'da dene:**
   `http://127.0.0.1:8000/docs` → POST /api/cameras'ı test et
