# Latest Camera/NVR Connectivity Note

- 2026-07-16: Kurumsal guvenlik/DDD/SOLID bulgulari duzeltildi. JWT ve kamera sifreleme anahtarlari placeholder/fallback kabul etmeden fail-fast dogrulaniyor; scan istekleri host/port/CIDR ve maksimum adres limitleriyle kisitlandi; login/change-password ve kamera/NVR mutasyonlari audit log'a yaziliyor; CORS method/header wildcard kaldirildi; frontend auth state sessionStorage'a tasindi; stream token URL query yerine ilk WebSocket mesajiyla gonderiliyor; kamera/NVR parola sifreleme route katmanindan use-case icine alindi; stream manager ve health checker somut DB/repository importlari yerine dependency factory ile calisiyor.

- Kamera/NVR bağlantı incelemesi ve yapılan düzeltmeler için `Docs_Obsidian/05_Camera_NVR_Connectivity_Notes.md` dosyasına bakın.
- 2026-06-18: Illustra i610 için 7778 portu + `/primarystream` yolu eklendi; kamera ekleme/taramada isteğe bağlı alternatif RTSP port denemesi, kamera/NVR RTSP doğrulamalarına zaman sınırı ve NVR import sırasında erişilebilir endpoint seçimi eklendi.
- 2026-06-18: `/primarystream` doğru i610 path'i otomatik taramada önceliklendirildi, tarama port ön kontrolüne bağımlı olmaktan çıkarıldı, NVR import gerçek frame doğrulamasıyla sıkılaştırıldı ve Kameralar ekranına RTSP "Test Et" tanısı eklendi.
- 2026-06-19: i610 gibi anonim RTSP ile frame veren cihazlar için kimlik bilgili URL başarısız olursa anonim frame fallback eklendi; kamera tarama tekil hostname kabul edecek şekilde genişletildi.
- 2026-06-19: NVR import, ONVIF URL frame vermezse kanal numarasından alternatif NVR RTSP path/port adaylarını deneyip başarısızlıkta aday bazlı DESCRIBE/Auth Frame/Anon Frame tanısı döndürecek şekilde genişletildi.
- 2026-06-19: OpenCV RTSP frame okuma TCP zorlamasından çıkarılıp varsayılan/UDP/TCP profillerini deneyen hale getirildi; NVR import adayları ve timeout'ları frontend 120s aşımını önlemek için kısaltıldı, HTTP timeout 300s yapıldı.
- 2026-06-22: Müşteri paketleme zinciri incelendi. Mevcut üretilmiş pakette `backend/data/rtsp_paths.json` bulunmadığı doğrulandı; paketleme scriptine `backend/data` kopyalama sonrası `rtsp_paths.json` varlık ve SHA-256 eşitlik kontrolü eklendi.
- 2026-06-22: Müşteri NVR logları incelendi. Frame vermeyen `DESCRIBE=OK` endpoint'in INACTIVE kamera olarak kaydedilmesi kaldırıldı; NVR import artık yalnızca gerçek frame doğrulanırsa kaydeder. RTSP URL içindeki şifre console logunda maskelenir ve bağımsız kamera tanı mesajından ilgisiz NVR yetki ifadesi çıkarıldı.
- 2026-06-22: Çok istemcili canlı yayın logları incelendi. Yayının kamera başına tek RTSP producer ile broadcast edildiği, ancak dashboard'un 84 kameranın tamamı için aynı anda WebSocket açarak 16 iş parçacıklı RTSP/JPEG/AI havuzunu doldurduğu doğrulandı. Kamera kartları yalnızca görünür/yakın olduklarında abone olacak şekilde değiştirildi; backend yeni aboneye iki saniyeden güncel son kareyi anında verir ve frontend geçici WebSocket kesintilerinde artan beklemeyle yeniden bağlanır.
- 2026-06-23: Canlı yayın protokolü Base64 JSON frame yerine metadata JSON + binary JPEG frame modeline geçirildi. `/api/streams/{camera_id}` WebSocket endpoint'i `profile=grid|live|alarm` parametresine göre istemciye gönderim hızını sınırlar: grid 4 FPS, live 15 FPS, alarm 2 FPS. Frontend hook'u eski Base64 JSON mesajlarıyla geriye dönük uyumlu kalır, binary JPEG için object URL kullanır ve kaynakları bağlantı kapanırken serbest bırakır.
- 2026-06-23: Kamera akış üreticisi istemci profiline duyarlı hale getirildi. Grid/alarm/live aboneliklerine göre RTSP okuma döngüsü 4 FPS / 2 FPS / 15 FPS hedeflerine yaklaşacak şekilde ayarlanır; izleyici kalmayınca producer hemen sönmek yerine kısa bir sıcak tutma süresi uygular. Bu, tekrar açılan canlı izleme ekranında ilk kare gecikmesini azaltmayı hedefler.
- 2026-06-23: Frontend başlangıç yükü route bazlı lazy-loading ile ayrıştırıldı. `DashboardPage`, `CamerasPage`, `NVRPage`, `AlarmsPage`, `SettingsPage` ve `AppLayout` ayrı chunk'lara taşındı; build sırasında oluşan tek büyük bundle bölünerek ilk yükleme hafifletildi.
- 2026-06-23: Aynı kamera için tekrar eden WebSocket bağlantıları frontend tarafında paylaşımlı stream registry ile birleştirildi. `useCameraStream` artık her mount için yeni soket açmak yerine kamera başına tek bağlantıyı paylaşır; grid/live/alarm abonelikleri arasında en yüksek öncelikli profil seçilir ve binary frame object URL yaşam döngüsü merkezi yönetilir.
- 2026-06-23: Paylaşılan stream registry için kısa yaşam süresi (retention) eklendi. Son abonelik kapandığında bağlantı anında parçalanmak yerine birkaç saniyelik kapatma gecikmesi uygulanır; kullanıcı aynı kamerayı kısa aralıkla tekrar açtığında mevcut websocket tekrar kullanılır ve yeniden bağlanma maliyeti düşer.
- 2026-06-23: Shared stream registry için reconnect debounce eklendi. Aynı kameraya ait abonelikler art arda mount olurken veya profil değişirken websocket yeniden kurulumu kısa bir gecikmeyle tek bir kez yapılır; bu, dashboard ve tam ekran kamera geçişlerinde soket churn'ünü azaltır.
- 2026-06-24: Shared stream registry görünürlük farkındalıklı hale getirildi. Sekme gizliyken websocket koparsa anında retry yapılmaz; görünür olduğunda pending reconnect tetiklenir. Bu, arka planda açık kalan dashboardlarda gereksiz ağ ve CPU kullanımını azaltır.
- 2026-06-24: Kamera akış producer'ı capture ve AI tespiti olarak ayrıştırıldı. RTSP okuma ve JPEG encode artık ana döngüde kalıyor; AI tespiti arka planda ayrı görev olarak aynı kare üzerinde çalışıyor. Bu, ilk kare gecikmesini ve capture sırasında oluşan blokajı azaltmayı hedefler.
- 2026-06-24: OpenCV RTSP okuyucu açılışta yakalanan ilk kareyi cache'leyip sonraki ilk tüketimde kullanacak şekilde güncellendi. Böylece yeni bağlantıda `cap.read()` ile alınan ilk kare boşa atılmıyor; ilk görüntü ekrana daha hızlı düşüyor.
- 2026-06-24: OpenCV RTSP okuyucu cihaz bazlı warm-up profil kullanan ve ardışık hata sayısına göre backoff yapan hale getirildi. Illustra i610 / `7778` / `primarystream` gibi cihazlarda daha kısa open/read timeout ve daha sık retry uygulanırken, genel ve NVR bağlantılarında daha temkinli bir retry penceresi korunuyor.
- 2026-06-24: Kamera detaylarındaki RTSP test modalına canlı akış telemetrisi eklendi. Producer çalışma durumu, subscriber sayısı, aktif profil, son frame yaşı ve RTSP open/failed sayaçları artık kullanıcıya görünür; bu, frame yok ama DESCRIBE OK olan durumları daha hızlı ayırt etmeyi sağlar.
- 2026-06-24: Frontend Vite build kökü açıkça sabitlendi; Windows path çözümlemesinde oluşan HTML emit hatası giderildi ve üretim build'i tekrar stabil hale geldi.

- 2026-07-03: Proje dosya agaci, izlenen model/paket dosyalari ve runtime ciktilari incelendi. `.gitignore`, yerel veritabani/env/cache, frontend build, musteri paket ciktilari, paketleme cache'i ve yerel AI arac dizinlerini disarida birakacak sekilde guncellendi; `backend/models/yolov8n.onnx` ve `backend/data/rtsp_paths.json` kaynak varlik olarak korunuyor.
- 2026-07-03: GitHub remote deposunun bos oldugu ve ilk push'un eski commit gecmisindeki paket/cache dosyalarini gonderecegi dogrulandi. Eski gecmis yerel yedek branch'te korunarak `main` dalinin temiz kaynak commit'iyle yeniden kurulmasi planlandi.
- 2026-07-13: Varsayılan `admin/admin123` otomatik seed davranışı kaldırıldı; ilk admin yalnızca `INITIAL_ADMIN_USERNAME` ve `INITIAL_ADMIN_PASSWORD` env değerleriyle veya `scripts/create_user.py` ile oluşturulur. CORS originleri env kontrollü hale getirildi. WebSocket canlı akış ana JWT yerine `/api/cameras/{id}/stream-token` üzerinden alınan kısa ömürlü stream token kullanır. Frontend lint hataları temizlendi ve frontend dosya başlığı yorumları tamamlandı.
- 2026-07-13: İnsan tespiti alarmı geldiğinde frontend kısa sesli uyarı çalacak şekilde güncellendi. Ses açık/kapalı durumu ve ses süresi Genel Ayarlar ekranından ayarlanır; değerler tarayıcıda kalıcı `kamera-system-settings` store'unda saklanır.

# Current State & Task Tracker

## What has been done (Completed)

- [x] **Phase 1: Project Skeleton** — FastAPI, SQLite, venv, CORS
- [x] **Phase 2: Domain Layer** — Camera, Alarm, User entities + tüm interfaces
- [x] **Phase 3: Infrastructure Layer** — SQLAlchemy modeller, repositoryler, ONNX servisi, OpenCV stream okuyucu
- [x] **Phase 4: Application Layer**
  - `ProcessFrameUseCase` — kare okuma → AI inference → cooldown → snapshot → alarm
  - `CameraUseCases` — CRUD + AES-256 şifre entegrasyonu
  - `NVRUseCases` — NVR CRUD + şifre entegrasyonu
  - `CameraWorkerManager` — asyncio + ThreadPoolExecutor ile arka plan tespit döngüsü
- [x] **Phase 5: Presentation Layer**
  - REST endpoints: `/cameras`, `/alarms`, `/users`, `/nvrs`, `/auth/login`
  - WebSocket: `/streams/{camera_id}` — canlı görüntü + AI tespit
  - FastAPI lifespan ile uygulama başlangıcında aktif kameralar için worker otomatik başlar
- [x] **Güvenlik**
  - AES-256-GCM şifreleme: kamera ve NVR şifreleri veritabanında şifreli saklanır
  - JWT (HS256): `/auth/login` endpoint'i erişim token'ı üretir
  - `get_current_user` dependency ve rol tabanlı yetkilendirme backend API rotalarına entegre edildi
- [x] **NVR Desteği**
  - `NVR` domain entity, SQLAlchemy model, repository
  - `POST /nvrs/{id}/probe` — ONVIF GetProfiles ile kanal önizleme
  - `POST /nvrs/{id}/import` — tüm kanalları sisteme otomatik kaydet
  - `Camera.nvr_id` FK ile kamera ↔ NVR ilişkisi
  - `Camera.brand`, `Camera.model` ONVIF'ten otomatik doldurulan alanlar
- [x] **AI Model**
  - `yolov8n.onnx` `backend/models/` içinde mevcut
  - Model path artık mutlak (`__file__` bazlı), CWD bağımsız

## ⚠️ Yapılması Gereken Manuel Adımlar

### 1. Veritabanı Migrasyonu
Mevcut `nvr_system.db` varsa:
```
cd backend
venv\Scripts\python.exe scripts/migrate_add_nvr_and_camera_fields.py
```

### 2. .env Dosyası Oluştur
```
copy .env.example .env
# .env dosyasını düzenle: CAMERA_ENCRYPTION_KEY ve JWT_SECRET_KEY doldur
```
Değer üretmek için:
```
venv\Scripts\python.exe -c "import os,base64; print(base64.b64encode(os.urandom(32)).decode())"
```

## ✅ Backend Bug Düzeltmeleri (Tamamlandı)

- [x] `CameraWorkerManager.__init__` `password_service` parametresi eklendi
- [x] `OpenCVStreamReader(password_service=...)` argümanı düzeltildi
- [x] `_stop_flags.get(camera_id, True)` → `False` (loop başlamıyordu)
- [x] `cam_use_cases.camera_repository.update()` — architecture violation → `cam_use_cases.update_camera()` ile düzeltildi
- [x] `CameraUseCases.update_camera()` metodu eklendi
- [x] `users.py` plain text şifre → `passlib` bcrypt hash
- [x] `ICameraRepository` Protocol'üne `list_by_nvr()` eklendi
- [x] `nvrs.py` gereksiz `NVRProbeRequest` import'u kaldırıldı
- [x] `python-dotenv` requirements.txt'e eklendi
- [x] `backend/README.md` oluşturuldu

## Next Steps (To-Do)

- [x] **JWT Koruması** — `get_current_user` ve rol tabanlı yetkilendirme (admin/operator/viewer) tüm backend API rotalarına entegre edildi, frontend token yönetimi düzeltildi.
- [x] **Kullanıcı yönetimi** — admin korumalı kullanıcı CRUD endpoint'leri ve CLI seed scripti mevcut; otomatik varsayılan admin kaldırıldı.
- [x] **Arka plan worker iyileştirme** — kamera offline olduğunda `CAMERA_OFFLINE` alarmı üretilmesi, kameranın durumunun ERROR yapılması ve bağlantı geri geldiğinde alarmın otomatik RESOLVED olarak kapatılması sağlandı.
- [x] **WS-Discovery** — `WSDiscovery` kütüphanesi entegre edildi, `/nvrs/discover` API ucu ve ön yüzde "Ağdaki Cihazları Tara" butonu/modalı ile entegrasyonu tamamlandı.
- [x] **Frontend** — React 19 + TypeScript + Vite + TailwindCSS v4 statik arayüz (tam ekran canlı kamera izleme ve kartlara tıklayarak izleme eklendi).
- [x] **Şifre değiştirme** — kullanıcı kendi şifresini `/auth/change-password` ile, admin kullanıcı şifresini `/users/{id}` ile, kamera/NVR şifresi PATCH endpoint'leriyle güncelleyebilir.


## API Özeti

| Method | Endpoint | Açıklama |
|---|---|---|
| POST | /api/auth/login | JWT token al |
| GET | /api/cameras/ | Tüm kameraları listele |
| POST | /api/cameras/ | Kamera ekle |
| PATCH | /api/cameras/{id}/status | Kamera aktif/pasif — worker başlar/durur |
| DELETE | /api/cameras/{id} | Kamera sil |
| GET | /api/nvrs/ | Tüm NVR'ları listele |
| POST | /api/nvrs/ | NVR ekle |
| POST | /api/nvrs/{id}/probe | ONVIF ile kanalları önizle |
| POST | /api/nvrs/{id}/import | Kanalları sisteme aktar |
| GET | /api/alarms/camera/{id} | Kamera alarmları |
| POST | /api/alarms/{id}/acknowledge | Alarm onayla |
| WS | /api/streams/{id} | Canlı görüntü + AI |
| GET | /api/health | Sistem durumu |

## Project Audit

- [x] Profesyonel VMS/NVR/AI kamera sistemleri araştırıldı.
- [x] Backend, frontend, UX, güvenlik ve operasyon eksikleri çıkarıldı.
- [x] Detaylı yapılacaklar listesi `Docs_Obsidian/04_Project_Audit_and_Todo.md` dosyasına eklendi.
- [x] Doğrulama: `npm run build` ve `python -m compileall src` başarılı.
