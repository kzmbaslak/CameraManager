# Latest Camera/NVR Connectivity Note

- 2026-07-23: Kamera ONVIF onizleme sonucu capability ozetiyle genisletildi. Backend GetCapabilities sonucundan Media, Events, PTZ, Imaging ve Analytics servis desteklerini okur; kamera ekleme/duzenleme ONVIF test paneli bu kabiliyetleri rozetlerle gosterir.
- 2026-07-23: Kamera AI ayarlari icin hazir hassasiyet profilleri eklendi. Kamera duzenleme modalinda Hassas, Dengeli ve Siki profilleri confidence, IoU, cooldown, frame stride ve AI genislik degerlerini birlikte ayarlar; operator profili sectikten sonra alanlari elle ince ayarlayabilir.
- 2026-07-23: Desktop sidebar daraltma tercihi eklendi. Operator genis ekranlarda sol navigasyonu ikon moduna alabilir; tercih `localStorage` icinde `kamera-sidebar-collapsed` anahtariyla kalici saklanir. Mobil drawer davranisi ayni kalir.
- 2026-07-23: Frontend yetki matrisi backend RBAC ile hizalandi. `viewer` rolu artik alarm onaylama/kapatma/yanlis alarm isaretleme, operasyon notu, kanit indirme ve CSV rapor export aksiyonlarini arayuzde gormez; bu aksiyonlar `operator` ve `admin` ile sinirlidir. Kullanici rol aciklamasi da izleyiciyi yalnizca goruntuleme/inceleme olarak tanimlar.
- 2026-07-23: Tarama/import satir validasyonlari eklendi. Kamera tarama sonucunda secili satirlarda bos veya tekrarlanan kamera adi kaydetmeden engellenir ve hata ilgili satir input'unda gosterilir. NVR kesif/toplu ekleme sonucunda secili satirlar icin bos/tekrarlanan NVR adi, bos host ve gecersiz ONVIF port satir seviyesinde gosterilir.
- 2026-07-23: Alarm operasyon raporu arayuze eklendi. Alarmlar sayfasi mevcut filtrelere gore acik alarm, yuksek oncelik, yanlis alarm orani ve ortalama cozum suresi metriklerini gosterir; filtrelenmis alarm listesi kamera, durum, onem, operator notu, cozum nedeni, cozum suresi ve snapshot hash alanlariyla CSV olarak indirilebilir.
- 2026-07-23: Alarm kanit snapshot akisi ham ve kutulu kanit olarak ayrildi. Yeni insan tespiti alarmlarinda `snapshot_path` ham/adli goruntu olarak saklanir, `snapshot_annotated_path` ise tum insan kutulari ve confidence etiketleri cizilmis operator kaniti olarak uretilir; her iki dosya icin SHA-256 alani tutulur. `/api/alarms/{id}/snapshot/annotated` endpoint'i kutulu kaniti dondurur, alarm detay paneli kutulu kaniti ana preview yapar ve ham kaniti ayri indirilebilir tutar.
- 2026-07-23: Yonetim formlarinda alan bazli dogrulama standartlastirildi. Kamera ekleme/duzenleme, NVR ekleme/duzenleme ve kullanici ekleme/duzenleme formlari artik ortak `formValidation` yardimcisiyla zorunlu ad/host, port araligi, parola uzunlugu ve kamera AI sayisal araliklarini kaydetmeden denetler; hata metinleri ilgili input altinda ARIA baglantili olarak gorunur.
- 2026-07-21: Canli insan tespiti BoundingBox akisi genisletildi. Backend `ProcessFrameUseCase` artik alarm sonucunun yaninda tum insan tespitlerini, confidence skorlarini, kaynak kare boyutunu ve tespit zamanini `DetectionAnalysisResult` olarak dondurur. `CameraStreamManager` son tespit metadata'sini 5 saniye saklayip WebSocket JSON mesajlarina `detections`, `frame_width`, `frame_height`, `detected_at` alanlariyla ekler. Frontend kamera karti ve tam ekran modal artik coklu insan kutularini grid icin `cover`, tam ekran icin `contain` olceklemesiyle cizer. Dashboard'a alarm akisi, canli stream sagligi, guvenlik kontrolu ve kisayol hatirlatmalarini bir arada gosteren operator destek paneli eklendi.
- 2026-07-21: Guvenlik durusu gorunurlugu eklendi. `/api/security/posture` endpoint'i JWT secret, kamera sifreleme anahtari, CORS wildcard riski, HTTPS bayragi, secure cookie/refresh-flow eksigi ve stream token TTL/aktarim modelini operator/admin icin raporlar. Dashboard operator destek paneli bu endpoint'i 60 saniyede bir okuyup bekleyen sertlestirme madde sayisini gosterir.
- 2026-07-21: Alarm inceleme akisi iyilestirildi. `/api/alarms/{id}/snapshot` endpoint'i alarm kanit snapshot'ini path traversal kontroluyle servis eder. Alarmlar sayfasina "Incele" aksiyonu ve sag detay paneli eklendi; panel snapshot preview, snapshot indirme, alarm metadata'si, "Canli Ac" ve "Onayla" aksiyonlarini tek yerde sunar.
- 2026-07-22: Alarm kanit butunluk bilgisi eklendi. Alarm domain/model/schema zincirine `snapshot_sha256` alani eklendi; yeni insan tespiti snapshot'lari kaydedilirken SHA-256 hesaplanir. Snapshot endpoint'i eski kayitlarda hash'i geriye donuk hesaplayip DB'ye yazar, `X-Snapshot-SHA256` header'i dondurur ve `alarm.snapshot.access` audit kaydi olusturur. Alarm detay paneli snapshot dosya adini ve SHA-256 degerini gosterir.
- 2026-07-22: Audit log gorunurlugu eklendi. JSONL audit dosyasindan son olaylari okuyan `read_audit_events` yardimcisi ve admin yetkili `/api/audit/events` endpoint'i eklendi. Sistem ve Kullanicilar ekraninda son 50 audit olayi, aksiyon, aktor, IP ve metadata ile 30 saniyede bir yenilenen tabloda gosterilir; adminler olaylari metin/durum filtresiyle daraltip gorunen sonucu CSV olarak indirebilir.
- 2026-07-22: Audit retention politikasi eklendi. `audit.log` varsayilan 5 MB sinirini (`AUDIT_MAX_BYTES`) asinca zaman damgali `audit-*.log` arsivine dondurulur; arsivler varsayilan 180 gunluk `AUDIT_RETENTION_DAYS` politikasina gore temizlenir.
- 2026-07-22: Audit butunluk zinciri eklendi. Yeni audit olaylari `previous_hash`, `event_hash` ve `hash_algorithm` alanlariyla yazilir; `AUDIT_CHAIN_SECRET` tanimliysa HMAC-SHA256, degilse SHA-256 kullanilir. Admin audit tablosu kisa zincir parmak izini gosterir, CSV cikti tam hash alanlarini icerir.
- 2026-07-22: Merkezi audit arsivi entegrasyonu eklendi. `AUDIT_WEBHOOK_URL` tanimliysa her audit olayi yerel dosyaya yazildiktan sonra JSON olarak merkezi log/SIEM endpoint'ine POST edilir; `AUDIT_WEBHOOK_TOKEN` Bearer token olarak, `AUDIT_WEBHOOK_TIMEOUT_SECONDS` ise gonderim zaman asimi olarak kullanilir.
- 2026-07-22: Guvenlik durusu endpoint'i audit sertlestirme sinyalleriyle genisletildi. `/api/security/posture` artik `AUDIT_CHAIN_SECRET` ve HTTPS tabanli `AUDIT_WEBHOOK_URL` durumunu raporlar; Dashboard guvenlik karti audit HMAC/SIEM durumunu tek satirda gosterir. `.env.example` audit chain, retention ve webhook ayarlariyla guncellendi.
- 2026-07-22: Ortak UI erisilebilirligi iyilestirildi. `Input` hata metnini `aria-describedby`/`aria-invalid` ile input'a baglar; `Modal` artik `role=dialog`, `aria-modal` ve baslik iliskisiyle acilir; `Button` varsayilan `type=button` kullanir; `Table` opsiyonel ekran okuyucu caption ve bos durum `aria-live` destegi aldi.
- 2026-07-22: Parola input erisilebilirligi tamamlandi. `PasswordInput` hata metnini `aria-describedby`/`aria-invalid` ile alanin kendisine baglar; sifre goster/gizle butonu mevcut ikonlu erisilebilir aksiyon olarak korunur.
- 2026-07-22: Liste siralama kontrolleri eklendi. Kamera, kayit cihazi ve kullanici listeleri filtrelenmis sonucu ad, durum/aktiflik, host/rol veya en yeni kayit secimlerine gore client-side siralayabilir; siralama kontrolleri `aria-label` tasir ve ana tablolar ekran okuyucu caption'i kullanir.
- 2026-07-22: Ilk kurulum preflight kontrolu eklendi. `collect_setup_checks` `.env` dosyasi, `backend/models/yolov8n.onnx`, zorunlu SQLite tablo/kolonlari ve aktif admin kullanicisini denetler. `/api/setup/status` operator/admin icin hazirlik sonucunu dondurur; `/api/security/posture` ayni eksikleri sertlestirme bulgularina ekler. Backend README audit env ve setup status endpoint'leriyle guncellendi.
- 2026-07-22: Script tabanli backup/restore akisi eklendi. `backend/scripts/backup_system.py` SQLite DB'yi backup API ile tutarli kopyalayip `.env`, `backend/data`, `models/yolov8n.onnx` ve `snapshots` dosyalarini SHA-256 manifestli zip arsivine alir. `backend/scripts/restore_system.py` manifest/hash dogrulamasi yapar, guvenli path siniri uygular ve dosya yazmak icin `--force` ister; `--dry-run` dogrulama modu vardir.
- 2026-07-22: Kamera bazli AI frame stride ve dusuk cozunurluk ornekleme ayarlari eklendi. Kamera model/schema/repository zincirine `ai_frame_stride` ve `ai_inference_width` alanlari eklendi; stream manager AI gorevlerini stride'a gore seyrekletir, `ProcessFrameUseCase` AI karesini hedef genislige kucultur ve bounding box koordinatlarini orijinal kareye geri olcekler. Kamera duzenleme modalinda bu ayarlar ve stream telemetrisinde AI provider/stride/genislik gorunur.
- 2026-07-22: Oturum suresi UX sertlestirmesi eklendi. Frontend JWT `exp` alanini okuyup `sessionStorage` auth state icinde `expiresAt` olarak saklar; API interceptor suresi dolmus token ile istek cikmadan oturumu temizler ve login ekraninda oturum suresi mesajini gosterir. Ana layout son 5 dakikada yapiskan uyarı bandi ve tek tusla cikis aksiyonu gosterir.
- 2026-07-22: Kamera bazli AI ayarlari ve ROI altyapisi eklendi. Kamera entity/model/schema/repository zincirine confidence threshold, IoU threshold, alarm cooldown, aktif saat baslangic/bitis ve normalize ROI poligon alanlari eklendi. ONNX inference artik kamera bazli threshold/IoU ile calisir; `ProcessFrameUseCase` aktif saat disinda tespiti atlar ve ROI poligon disindaki insan kutularini eler. Kameralar duzenleme modalina AI alarm ayarlari paneli eklendi. Eski SQLite kurulumlari icin `scripts/migrate_add_camera_ai_settings.py` ve startup idempotent kolon kontrolu eklendi.
- 2026-07-22: Alarm operasyon alanlari eklendi. Alarm entity/model/schema/repository zincirine `assigned_to`, `operator_note`, `resolution_reason` alanlari eklendi. `/api/alarms/{id}` PATCH atama/not gunceller; `/api/alarms/{id}/resolve` cozum nedeni ile kapatir ve audit log yazar. Alarmlar detay panelinde atanan kisi, operator notu, not kaydetme ve cozuldu olarak kapatma akisi eklendi. Eski SQLite kurulumlari icin `scripts/migrate_add_alarm_operation_fields.py` ve startup idempotent kolon kontrolu eklendi.
- 2026-07-22: Kamera saglik gecmisi eklendi. Health checker her aktif kamera icin TCP erisilebilirlik, latency ve hata nedenini `camera_health_samples` tablosuna kaydeder, 7 gunden eski ornekleri temizler. `/api/cameras/{id}/diagnostics/health-history` endpoint'i son ornekleri, erisilebilirlik yuzdesini ve son hata/latency ozetini dondurur. Kameralar sayfasindaki RTSP test modalina saglik gecmisi mini trend grafigi eklendi. Eski SQLite kurulumlari icin `scripts/migrate_add_camera_health_samples.py` eklendi ve mevcut veritabani uzerinde calistirildi.
- 2026-07-22: Yanlis alarm ve onem seviyesi akisi eklendi. Alarm domain/model/schema/repository zincirine `severity` ve `false_positive` alanlari eklendi; insan tespiti ve kamera offline alarmlari varsayilan yuksek onemle baslar. `/api/alarms/{id}/false-positive` endpoint'i alarmi tek aksiyonla yanlis alarm olarak kapatir ve audit log yazar. Alarmlar detay panelinde onem seviyesi secimi ve "Yanlis Alarm" hizli kapatma aksiyonu eklendi. `scripts/migrate_add_alarm_operation_fields.py` ve startup kolon kontrolu bu alanlari idempotent ekler.
- 2026-07-22: Kameralar listesine operator hiz filtreleri eklendi. Kamera adi, IP, RTSP path, marka/model ve NVR ID uzerinden arama; izleme durumu ve AI acik/kapali filtreleri client-side calisir. Liste sayaci filtrelenen/toplam kamera oranini gosterir ve tek tusla filtre sifirlama vardir.
- 2026-07-22: NVR listesine operator hiz filtreleri eklendi. NVR adi, IP, marka/model ve kullanici adi aramasi ile aktif/pasif filtreleri client-side calisir. Liste sayaci filtrelenen/toplam kayit cihazi oranini gosterir ve filtreler tek tusla sifirlanir.
- 2026-07-22: Kullanici listesine operator hiz filtreleri eklendi. Kullanici adi aramasi, rol filtresi ve aktif/pasif filtresi Ayarlar ekranindaki kullanici tablosunda client-side calisir. Liste sayaci filtrelenen/toplam kullanici oranini gosterir ve filtreler tek tusla sifirlanir.
- 2026-07-22: Tarayici `confirm()` kullanan silme akislari erisilebilir onay modalina tasindi. Ortak `ConfirmDialog` bileseni eklendi; kamera, NVR ve kullanici silme islemleri artik uygulamanin modal/Button tasarimi icinde aciklama, iptal ve yuklenme durumuyla calisir. Frontend kaynaklarinda `confirm()`/`alert()` kalmadigi dogrulandi.
- 2026-07-22: Sifre alanlari ortak gorunurluk kontrollu input'a tasindi. `PasswordInput` bileseni eklendi; login, kamera ekleme/duzenleme/tarama, NVR ekleme/duzenleme/tarama/import ve kullanici ekleme/duzenleme formlarinda sifreyi goster/gizle aksiyonu erisilebilir ikonlu butonla calisir.
- 2026-07-22: Kamera duzenleme modalina kayitli RTSP baglanti testi eklendi. Operator modal disina cikmadan TCP/DESCRIBE/frame sonucunu, maskelenmis RTSP URL'yi ve hata mesajini gorebilir. Formda kaydedilmemis baglanti degisikligi varsa testin mevcut kayitli degerlerle calistigi acikca belirtilir.
- 2026-07-22: Kamera RTSP onizleme testi eklendi. `/api/cameras/diagnostics/rtsp-preview` endpoint'i kaydetmeden host/port/path/kullanici/sifre alanlariyla TCP, DESCRIBE ve frame testi yapar; duzenleme formunda sifre bos birakilirsa backend kayitli sifreyi guvenli sekilde kullanir. Kamera ekleme ve duzenleme modallarinda operator kaydetmeden form degerlerini test edebilir.
- 2026-07-23: Kamera ONVIF onizleme testi eklendi. `/api/cameras/diagnostics/onvif-preview` endpoint'i kaydetmeden host/ONVIF port/kullanici/sifre ile GetDeviceInformation ve stream URI profil testlerini calistirir; duzenleme formunda sifre bos birakilirsa backend kayitli sifreyi kullanir. Kamera ekleme ve duzenleme modallarinda ONVIF cihaz bilgisi, profil/stream sayisi ve maskelenmis ilk RTSP URI gorunur.
- 2026-07-23: Yonetim listeleri icin server-side pagination eklendi. Kamera, NVR ve kullanici liste endpoint'leri `paginated=true`, `page`, `page_size`, arama, filtre ve siralama parametreleriyle sayfali yanit dondurur; eski array yaniti varsayilan olarak korunur. Kameralar, Kayit Cihazlari ve Sistem/Kullanicilar ekranlari sayfa boyutu secimi, onceki/sonraki kontrolu ve backend toplam sonucu kullanir.
- 2026-07-22: Global toast bildirim standardi eklendi. `toastStore` ve `ToastViewport` ile basarili/basarisiz islemler uygulama genelinde ayni gorsel dilde gosterilir. Kamera, NVR, kullanici ve alarm operasyonlarinda ekleme/guncelleme/silme/onaylama/cozum/yanlis alarm/kanal import aksiyonlari success veya danger toast uretir.
- 2026-07-22: Dashboard canli grid operator tercihleri eklendi. Izlenen kameralar ad, host veya durum metniyle hizli aranabilir; secilen 1x1/2x2/3x3/4x4 grid duzeni tarayicida kalici tutulur; dusuk bant modu grid kartlarini daha hafif `alarm` stream profiline gecirerek cok kamera izlerken ag/CPU yukunu azaltir. Grid kartlari surukle-birak ile siralanabilir ve operatorun kamera sirasi tarayicida saklanir. Tam ekran canli izleme modalinda 1, 2x2 ve 3x3 coklu kamera layout secimi eklendi.
- 2026-07-22: Frontend lint temizligi yapildi. Alarm detay drawer'i alarm degisiminde `key` ile yeniden mount olacak sekilde duzenlendi; snapshot yukleme ayri local state yerine React Query verisinden turetilir ve object URL temizligi cleanup effect'iyle yapilir. `npm run lint` ve `npm run build` basarili.
- 2026-07-22: Navigasyon dili operator konsoluna gore netlestirildi. Sidebar'da `Dashboard` yerine `Canli Izleme`, `NVR` yerine `Kayit Cihazlari`, ayarlar/kullanici bolumu icin `Sistem ve Kullanicilar` kullanilir. Yeni `/recorders` ve `/users` route'lari eklendi; eski `/nvr` ve `/settings` adresleri uyumluluk icin yeni route'lara yonlendirilir.
- 2026-07-22: Kucuk ekran ve tablet icin responsive navigasyon eklendi. Desktop'ta sabit sidebar korunur; mobilde ust bar menusu overlay drawer acar, arka plan tiklamasi veya nav secimi drawer'i kapatir.
- 2026-07-22: Frontend API hata mesaji standardi genisletildi. Ortak `getApiErrorMessage` yardimcisi eklendi; kamera, kayit cihazi, kullanici yonetimi ve alarm aksiyonlari backend `detail` alanini veya okunabilir fallback mesajini gosterir. Kamera ve kayit cihazi sayfalarindaki kopya hata cevirici fonksiyonlar ortak helper'a tasindi; cihaz ozelindeki ag hata aciklamalari wrapper ile korundu. Login hata mesaji guvenlik icin genel tutulur.
- 2026-07-17: NVR ONVIF probe akisi netlestirildi. ONVIF response parse islemi zeep `serialize_object` ile guclendirildi; kanal probe sonucuna `source` ve `diagnostic` alanlari eklendi. `/api/nvrs/{id}/probe/diagnostics` endpoint'i ONVIF basarisi, fallback kullanimi, hata mesaji ve kanal sayilarini doner. Frontend NVR kanal modalinda ONVIF Basarili / RTSP Fallback / Kanal Bulunamadi durumu ve kanal bazli kaynak rozeti gosterilir.
- 2026-07-17: Frontend tasarimi VMS/SOC operator konsolu stiline cekildi. Global renk paleti lacivert agirlikli temadan charcoal/nötr koyu gri tabana tasindi; alarm kirmizisi, uyari amber, aktif mavi, online yesil oncelik kodlari olarak ayrildi. Dashboard daha yogun ust durum bari ve sikilastirilmis video grid kullanir; kamera kartlari daha duz, daha az yuvarlak ve alarm durumunda belirgin kirmizi sinir/ribbon ile calisir. Sidebar, grid secici, modal, badge ve buton yuzeyleri ayni operasyonel gorsel dile uyarlandi.
- 2026-07-17: Alarm operator UX akisi iyilestirildi. Global alarm bildirimi artik kalici mudahale paneli gibi calisir; kullanici tek tusla "Sustur ve Onayla" yapabilir, 5 dakika sessize alabilir, tum yeni alarmlari toplu onaylayabilir ve alarmdan dogrudan canli goruntuye gecebilir. Tam ekran kamera modalina ayni alarm aksiyonlari ve Space/A/Enter/Esc kisayollari eklendi. Dashboard yeni alarm sayaci hizli sessize alma/toplu onay aksiyonlari tasir. Eski Vite CSS kalintilari temizlendi ve genel focus-visible halkasi eklendi.
- 2026-07-17: Alarm kisayol bilgileri arayuze yerlestirildi. Global alarm mudahale panelinde, Dashboard yeni alarm seridinde ve tam ekran kamera modalinda Space=Sustur, A=Onayla, Enter=Canli goruntu, Esc=Kapat komutlari kompakt kbd rozetleriyle gosterilir.
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
