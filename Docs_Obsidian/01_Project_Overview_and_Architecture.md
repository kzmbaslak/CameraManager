# Proje Genel Bakış ve Sistem Mimarisi (Project Overview & System Architecture)

## Genel Bakış (Overview)
Tamamen yerel (local), NVR'dan bağımsız, internet bağlantısı gerektirmeyen (offline) bir IP Kamera insan tespiti (human detection) sistemi. Kameralara RTSP/ONVIF üzerinden bağlanır, hareket algılama işlemini gerçekleştirir (ONVIF olayları veya yazılım aracılığıyla) ve insanları tespit etmek için AI çıkarımı (YOLOv8 ONNX) çalıştırır.

## Teknoloji Yığını (Tech Stack)
- **Arka Uç (Backend):** Python, FastAPI
- **Veritabanı (Database):** SQLite (SQLAlchemy ile birlikte)
- **Bilgisayarlı Görü (Computer Vision):** OpenCV (`cv2`)
- **Yapay Zeka Çıkarımı (AI Inference):** ONNX Runtime (YOLOv8 Nano `yolov8n.onnx`)
- **Kamera Protokolleri (Camera Protocols):** ONVIF (`onvif-zeep`), RTSP
- **Ön Uç (Frontend):** React 19 + TypeScript + Vite + TailwindCSS v4 (Statik dosyalar, internet bağlantısı gerektirmez)

## Alan Odaklı Tasarım (DDD - Domain-Driven Design) Mimarisi
Arka uç (backend), `backend/src/` dizininde 4 katmanlı olarak yapılandırılmıştır:
1. **Alan (Domain - `domain/`):** Kurumsal iş kurallarını (business rules), Varlıkları (Entities - örn. `Camera`, `Alarm`, `User`) ve Arayüzleri (Interfaces - örn. `ICameraRepository`, `IAIInferenceService`) içerir. Dışarıya bağımlılığı yoktur (FastAPI veya SQLAlchemy bile içermez).
2. **Uygulama (Application - `application/`):** Alan mantığını (domain logic) koordine eden Kullanım Senaryolarını (Use Cases - örn. `ProcessFrameUseCase`, `AddCameraUseCase`) içerir.
3. **Altyapı (Infrastructure - `infrastructure/`):** Dış dünya ile ilgili işlemler, veritabanı uygulamaları (örn. `SqlAlchemyCameraRepository`), OpenCV akış okuyucuları (stream readers), ONNX runtime sarmalayıcıları (wrappers).
4. **Sunum (Presentation - `presentation/`):** FastAPI uç noktaları (endpoints), WebSocket yöneticileri (managers), kullanıcı girdilerinin işlenmesi.

## Entegrasyon API (Integration API)
Sistem, (Hapishane Yönetim Sistemi gibi) diğer yerel projelerin alarmları ve anlık görüntüleri (snapshots) tüketebilmesi için yerel bir REST API ve Webhook mekanizması sağlar.
