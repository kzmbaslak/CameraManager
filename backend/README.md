# Kamera İzleme ve İnsan Tespiti — Backend

Tamamen yerel (offline) çalışan, NVR destekli, YOLOv8 tabanlı IP kamera insan tespit sistemi.

---

## Mimari

Proje **Domain-Driven Design (DDD)** ilkesine uygun 4 katmanlı yapıda tasarlanmıştır:

```
backend/
├── src/
│   ├── domain/          # Entity'ler, interface'ler, iş kuralları (hiç dış bağımlılık yok)
│   ├── application/     # Use case'ler, arka plan worker yöneticisi
│   ├── infrastructure/  # SQLAlchemy, OpenCV, ONNX, ONVIF, şifreleme
│   └── presentation/    # FastAPI route'ları, şemalar, bağımlılık enjeksiyonu
├── models/              # yolov8n.onnx — YOLOv8 nano ONNX modeli (elle yerleştirilmeli)
├── data/                # nvr_system.db — SQLite veritabanı (otomatik oluşur)
├── scripts/             # Veritabanı migrasyon scriptleri
├── main.py              # Uygulama giriş noktası
├── requirements.txt
└── .env.example
```

---

## Kurulum

### 1. Bağımlılıkları Kur

```bash
cd backend
python -m venv venv
venv\Scripts\activate       # Windows
pip install -r requirements.txt
```

> `onnxruntime-gpu` paketi CUDA varsa GPU'yu, yoksa otomatik CPU'yu kullanır.
> Farklı cihazlarda kod değişikliği gerektirmez.

### 2. YOLOv8 ONNX Modelini Yerleştir

```bash
# Ayrı bir ortamda modeli dışa aktar:
pip install ultralytics
python -c "from ultralytics import YOLO; YOLO('yolov8n.pt').export(format='onnx')"
# Oluşan yolov8n.onnx dosyasını backend/models/ altına koy
```

### 3. Ortam Değişkenlerini Ayarla

```bash
copy .env.example .env
```

`.env` dosyasını düzenle — iki değer üretmek için:

```bash
venv\Scripts\python -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

| Değişken | Açıklama |
|---|---|
| `CAMERA_ENCRYPTION_KEY` | Base64 ile kodlanmış 32 bayt AES anahtarı |
| `JWT_SECRET_KEY` | JWT imzalama anahtarı (rastgele uzun string) |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | Token geçerlilik süresi (varsayılan: 480 dakika) |
| `INITIAL_ADMIN_USERNAME` | İlk kurulumda DB boşsa oluşturulacak admin kullanıcı adı |
| `INITIAL_ADMIN_PASSWORD` | İlk kurulumda DB boşsa oluşturulacak admin şifresi |
| `CORS_ALLOWED_ORIGINS` | Virgülle ayrılmış izinli frontend origin listesi |
| `AUDIT_CHAIN_SECRET` | Audit kayıt zinciri için en az 32 karakterlik HMAC anahtarı |
| `AUDIT_MAX_BYTES` | `audit.log` arşive döndürülmeden önce izin verilen maksimum boyut |
| `AUDIT_RETENTION_DAYS` | Audit arşivlerinin saklanacağı gün sayısı |
| `AUDIT_WEBHOOK_URL` | Opsiyonel merkezi log/SIEM HTTPS endpoint'i |
| `AUDIT_WEBHOOK_TOKEN` | Opsiyonel audit webhook Bearer token değeri |
| `AUDIT_WEBHOOK_TIMEOUT_SECONDS` | Audit webhook gönderim zaman aşımı |

### 4. Veritabanını Hazırla

İlk çalıştırmada tablolar otomatik oluşur. Mevcut bir `nvr_system.db` varsa ve NVR desteği eklendiyse migrasyon scriptini çalıştır:

```bash
venv\Scripts\python scripts/migrate_add_nvr_and_camera_fields.py
```

Kurulum hazır durumunu API üzerinden görmek için oturum açmış operatör/admin kullanıcıyla:

```text
GET /api/setup/status
GET /api/security/posture
```

Bu kontroller `.env` varlığı, `backend/models/yolov8n.onnx`, veritabanı şeması ve aktif admin kullanıcısını raporlar.

### 5. Sunucuyu Başlat

```bash
venv\Scripts\python -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

---

## API Endpoint'leri

Swagger UI: `http://localhost:8000/docs`

### Kimlik Doğrulama

| Method | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/auth/login` | Kullanıcı adı + şifre ile JWT token al |

**İstek:**
```json
{ "username": "admin", "password": "parola123" }
```
**Yanıt:**
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

---

### Kullanıcı Yönetimi

| Method | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/users/` | Yeni kullanıcı oluştur |
| `GET` | `/api/users/` | Tüm kullanıcıları listele |

Şifreler bcrypt ile hashlenerek saklanır, düz metin asla veritabanına yazılmaz.

---

### Kamera Yönetimi

| Method | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/cameras/` | Kamera ekle |
| `GET` | `/api/cameras/` | Tüm kameraları listele |
| `GET` | `/api/cameras/{id}` | Kamera detayı |
| `PATCH` | `/api/cameras/{id}/status` | Kamera aktif/pasif — worker otomatik başlar/durur |
| `DELETE` | `/api/cameras/{id}` | Kamera sil |

**Kamera ekleme isteği:**
```json
{
  "name": "Giriş Kamerası",
  "host": "192.168.1.50",
  "rtsp_port": 554,
  "rtsp_path": "/stream1",
  "onvif_port": 80,
  "username": "admin",
  "password": "kamera_sifresi"
}
```

Şifreler AES-256-GCM ile şifrelenerek veritabanında saklanır.

---

### NVR Yönetimi

| Method | Endpoint | Açıklama |
|---|---|---|
| `POST` | `/api/nvrs/` | NVR cihazı ekle |
| `GET` | `/api/nvrs/` | Tüm NVR'ları listele |
| `GET` | `/api/nvrs/{id}` | NVR detayı |
| `DELETE` | `/api/nvrs/{id}` | NVR sil |
| `POST` | `/api/nvrs/{id}/probe` | ONVIF ile kanalları önizle (kaydetmez) |
| `POST` | `/api/nvrs/{id}/import` | Tüm kanalları sisteme kamera olarak aktar |

**NVR ekleme isteği:**
```json
{
  "name": "Ana Bina NVR",
  "host": "192.168.1.100",
  "onvif_port": 80,
  "username": "admin",
  "password": "nvr_sifresi"
}
```

**NVR probe yanıtı (kanal listesi):**
```json
[
  {
    "profile_token": "Profile_1",
    "profile_name": "Kanal 1",
    "manufacturer": "Hikvision",
    "model": "DS-7608NI-K2",
    "rtsp_url": "rtsp://192.168.1.100:554/Streaming/Channels/101"
  }
]
```

`POST /nvrs/{id}/import` çağrıldığında her kanal otomatik olarak `Camera` entity olarak kaydedilir; `brand`, `model` ve `nvr_id` alanları ONVIF'ten doldurulur.

---

### Alarm Yönetimi

| Method | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/api/alarms/camera/{camera_id}` | Kameraya ait alarmları listele |
| `POST` | `/api/alarms/{id}/acknowledge` | Alarmı onayla |

---

### Canlı Görüntü (WebSocket)

```
GET /api/cameras/{camera_id}/stream-token
WS  /api/streams/{camera_id}?token=<stream_token>
```

Bağlantı kurulduğunda sunucu:
1. Kameranın RTSP akışından kare okur
2. YOLOv8 ile insan tespiti yapar
3. Metadata bilgisini JSON, görüntü karesini binary JPEG olarak gönderir

**Gelen mesaj formatı:**
```json
{
  "frame": "<base64-jpeg>",
  "detections": [
    {
      "label": "person",
      "confidence": 0.87,
      "bounding_box": { "x": 120, "y": 45, "width": 80, "height": 160 }
    }
  ],
  "timestamp": "2024-01-15T10:30:00"
}
```

---

### Sistem Durumu

| Method | Endpoint | Açıklama |
|---|---|---|
| `GET` | `/api/health` | Aktif worker sayısı, AI servisi durumu |

---

## Canlı Akış ve Arka Plan İnsan Tespiti (CameraStreamManager)

`CameraStreamManager`, kamera başına TEK bir arka plan üretici (producer) `asyncio.Task` çalıştırır. Bu üretici RTSP'den kare okur, bağlı tüm WebSocket izleyicilerine (aynı ağdaki farklı cihazlar dahil) yayınlar (broadcast) ve `ai_detection_enabled=True` olan kameralarda kendi periyodunda (varsayılan ~2 FPS) insan tespiti yapar.

- Kaç istemci aynı kamerayı izlerse izlesin, kamera başına yalnızca TEK RTSP bağlantısı açılır.
- Canlı izleme görüntü hızı (`display_fps`, varsayılan 15) AI'nın tespit hızına bağlı kalmaz — ayrı yönetilir.
- Kare okuma ve ONNX inference, `ThreadPoolExecutor` içinde çalışır (event loop bloklanmaz).
- Cooldown mekanizması: Aynı kamera için belirli süre (varsayılan 60 sn) içinde tekrar alarm üretmez.
- Üretici, en az bir izleyici VEYA AI açıkken çalışır; AI kapalı ve hiç izleyici yoksa boşuna RTSP çekmemek için durur.
- Uygulama başladığında (`FastAPI lifespan`) AI açık aktif kameralar için üreticiler otomatik başlatılır.
- Kamera silindiğinde veya pasife alındığında tüm izleyici bağlantıları anında kapatılır ve üretici durur.

---

## Kamera RTSP Stream Okuma

`OpenCVStreamReader`, kameranın şifreli parolasını `PasswordEncryptionService` ile çözerek RTSP URL oluşturur:

```
rtsp://username:sifre@host:rtsp_port/rtsp_path
```

`cv2.VideoCapture` ile bağlantı kurulur ve tutulur; bağlantı koptuğunda otomatik yeniden bağlanma yapılır.

---

## İnsan Tespiti (YOLOv8 ONNX)

`ONNXInferenceService` YOLOv8 nano modelini kullanır:

1. Kare `640×640` piksel boyutuna letterbox ile yeniden boyutlandırılır.
2. ONNX Runtime'da inference yapılır.
3. COCO sınıf 0 (person) için eşik üstü tespitler alınır.
4. NMS (Non-Maximum Suppression) ile çakışan kutular temizlenir.
5. Her tespit için `BoundingBox` ve güven skoru döndürülür.

**GPU/CPU otomatik seçimi:** CUDA kuruluysa `CUDAExecutionProvider` kullanılır, yoksa `CPUExecutionProvider`'a düşer. Kod değişikliği gerekmez.

---

## Güvenlik

### Şifre Şifreleme (AES-256-GCM)

Kamera ve NVR şifreleri veritabanında asla düz metin olarak saklanmaz:

- **Algoritma:** AES-256-GCM (authenticated encryption)
- **Anahtar:** `CAMERA_ENCRYPTION_KEY` env değişkeninden yüklenir (base64, 32 bayt)
- **Format:** `base64(nonce[12B] + ciphertext)`
- **Her şifreleme** benzersiz rastgele nonce kullanır

### JWT Kimlik Doğrulama

- **Algoritma:** HS256
- **Anahtar:** `JWT_SECRET_KEY` env değişkeninden yüklenir
- **Token:** `POST /api/auth/login` ile alınır
- **Kullanım:** `Authorization: Bearer <token>` header'ı

### Kullanıcı Şifreleri (bcrypt)

Kullanıcı şifreleri `passlib` ile bcrypt kullanılarak hashlenir. Ham şifre hiçbir zaman veritabanına yazılmaz.

---

## Frontend Entegrasyonu

### HTTP İstekleri

Tüm API istekleri `http://localhost:8000/api` prefix'i ile yapılır.

Token alındıktan sonra her istekte header ekle:
```
Authorization: Bearer <access_token>
```

### WebSocket Bağlantısı

```javascript
const tokenResponse = await fetch(`/api/cameras/${cameraId}/stream-token`, {
  headers: { Authorization: `Bearer ${accessToken}` },
}).then((r) => r.json());

const ws = new WebSocket(`ws://localhost:8000/api/streams/${cameraId}?token=${tokenResponse.stream_token}`);
ws.onmessage = (event) => {
  if (typeof event.data !== 'string') {
    const img = document.getElementById('camera-feed');
    img.src = URL.createObjectURL(event.data);
  }
};
```

### Kamera Ekleme Akışı

1. `POST /api/nvrs/` → NVR ekle
2. `POST /api/nvrs/{id}/probe` → Kanalları önizle
3. `POST /api/nvrs/{id}/import` → Kanalları kaydet
4. `PATCH /api/cameras/{id}/status` body: `"ACTIVE"` → Worker başlar
5. WebSocket bağlan → Canlı görüntü al

---

## Notlar

- Sistem tamamen **offline** çalışır — internet bağlantısı gerekmez.
- WSDL dosyaları `onvif-zeep` paketi ile birlikte lokalde bulunur.
- WS-Discovery (`POST /nvrs/discover`) aktiftir ve `WSDiscovery` bağımlılığı requirements içinde bulunur.
- HTTP API endpoint'leri JWT/RBAC dependency'leriyle korunur; WebSocket canlı akış için kısa ömürlü stream token kullanılır.
