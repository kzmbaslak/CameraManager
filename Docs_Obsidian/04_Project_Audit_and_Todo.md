# Proje İnceleme ve Yapılacaklar Listesi

## Araştırma Özeti

Profesyonel kamera/NVR/VMS sistemleri yalnızca canlı görüntü göstermez; operasyon yönetimi platformu olarak çalışır. İncelenen örneklerde ortak desenler:

- Canlı izleme, kayıt arama, zaman çizelgesi ve kanıt dışa aktarma tek akışta sunulur.
- ONVIF profilleriyle cihaz/istemci uyumluluğu standartlaştırılır; video sistemleri için Profile S/T/G/M öne çıkar.
- NVR/VMS cihazları, kameralar, alarmlar, kullanıcılar, roller, sağlık durumu ve entegrasyonlar merkezi bir arayüzden yönetilir.
- AI analitik gerçek zamanlı, çoklu kamera, metadata üreten ve olay kural motoruna bağlanan bir pipeline olarak ele alınır.
- Operatör deneyimi hızlı alarm değerlendirme, olay geçmişi, arama, filtreleme, layout seçimi, rol tabanlı erişim ve sade durum göstergeleri üzerine kuruludur.

Kaynaklar:
- Axis Camera Station Pro: canlı izleme, kayıt arama/dışa aktarma, erişim kontrolü, özel ağ, action rule engine ve kullanıcı dostu arayüz vurgusu. https://www.axis.com/products/axis-camera-station-pro
- Milestone XProtect: merkezi, açık ve ölçeklenebilir video yönetimi; kamera/sensör/IoT entegrasyonu ve siber güvenlik vurgusu. https://www.milestonesys.com/products/software/xprotect/
- Genetec Security Center: video, erişim kontrolü, ALPR, iletişim ve alarm yönetimini tek platformda birleştirme. https://www.genetec.com/products/unified-security/security-center
- Network Optix Nx Witness: entegrasyon, AI analitik, özelleştirilebilir layout/kurallar, sağlık izleme, failover, API/SDK ve güvenlik. https://www.networkoptix.com/nx-witness
- ONVIF Profiles: Profile S/T/G/M gibi profillerle cihaz-istemci uyumluluğu. https://www.onvif.org/profiles/
- NVIDIA DeepStream: çoklu kamera, gerçek zamanlı streaming analytics, metadata, tracking ve GPU hızlandırmalı pipeline yaklaşımı. https://developer.nvidia.com/deepstream-sdk
- Ultralytics Predict Docs: RTSP/multi-stream, stream mode, frame stride, buffering ve detection argümanları. https://docs.ultralytics.com/modes/predict/

## Mevcut Proje Durumu

Güçlü taraflar:
- Backend DDD katmanlarına ayrılmış.
- Kamera, NVR, alarm, kullanıcı, JWT ve rol bazlı endpoint çekirdeği var.
- ONVIF probe/discover, RTSP okuma, YOLO ONNX inference, AES-256-GCM şifreleme ve WebSocket canlı izleme eklenmiş.
- Frontend React + TypeScript + Vite ile çalışıyor; `npm run build` başarılı.
- Backend kaynakları `python -m compileall src` ile derleniyor.

Riskler:
- Frontend kaynaklarında Türkçe metinler bazı dosyalarda bozuk karakterlerle görünüyor. Bu gerçek dosya encoding problemiyse kullanıcı arayüzüne de yansır.
- Script tabanlı SQLite migration sayısı artıyor; Alembic veya eşdeğer sürümlü migration yapısına geçilmezse kurulum/upgrade riski büyür.

## Kritik Eksikler

### P0 - Ürün Temeli

- Kayıt sistemi yok: sürekli/olay bazlı video kaydı, kayıt takvimi, retention, disk kotası ve otomatik silme eklenmeli.
- Playback yok: kamera bazlı zaman çizelgesi, olaydan önce/sonra izleme, hız kontrolü, snapshot/video dışa aktarma eklenmeli.
- Kanıt yönetimi yok: alarm snapshot dosyaları UI'da görüntülenmeli, indirilmeli, hash/audit bilgisi tutulmalı.
- Alarm operasyon akışı büyük ölçüde tamamlandı: yeni/onaylandı/çözüldü, atanan kullanıcı, not, önem seviyesi, olay kapatma nedeni, yanlış alarm işareti ve detay paneli var. Kalan iş bu operasyon verisini raporlama/eğitim seti akışına bağlamak.
- Audit log yok: kullanıcı girişleri, kamera/NVR değişiklikleri, alarm aksiyonları ve export işlemleri kayıt altına alınmalı.
- İlk kurulum akışı kısmen var: otomatik varsayılan admin kaldırıldı, env kontrollü ilk admin ve CLI seed scripti var. Kalan iş: `.env` kontrolü, model varlığı, DB migrasyonu ve kamera/NVR ekleme sihirbazını tek akışa bağlamak.

### P1 - Kamera/NVR Yönetimi

- ONVIF yetenek keşfi sınırlı: Profile S/T/G/M, stream profilleri, çözünürlük/FPS/codec, snapshot URI, event subscriptions ve PTZ capability okunmalı.
- PTZ desteği yok: pan/tilt/zoom, preset, patrol ve yetkiye bağlı PTZ kontrolü eklenmeli.
- Kamera sağlık metrikleri yetersiz: son frame zamanı, reconnect sayısı, FPS, latency, hata nedeni ve uptime gösterilmeli.
- NVR import deneyimi geliştirilmeli: daha önce eklenen kanallar işaretlenmeli, kanal ismi düzenlenebilmeli, toplu profil seçimi ve duplicate raporu sunulmalı.
- Kamera bağlantı testi kısmen tamamlandı: kamera listesinde ve kamera düzenleme modalında kayıtlı RTSP bağlantısı TCP/DESCRIBE/frame sonucu ve açıklayıcı hata mesajıyla test edilebiliyor. Kalan iş kaydedilmemiş form değerlerini test eden önizleme endpoint'i ve ONVIF testini aynı akışa eklemek.
- Çoklu saha/konum modeli yok: site, bina, kat, bölge gibi hiyerarşi ve ileride harita/floorplan görünümü için domain alanları eklenmeli.

### P1 - AI ve Olay Tespiti

- AI pipeline ayrıştırıldı: canlı yayın capture hattı artık ayrı çalışıyor, AI tespiti ise arka planda bağımsız görev olarak tetikleniyor. Kalan iş, tam anlamıyla tek capture hattı üzerinde düşük çözünürlüklü AI örnekleme ve daha akıllı frame stride kontrolü kurmak.
- RTSP açılış optimizasyonu ve kalıcı sağlık geçmişi eklendi: `OpenCVStreamReader` ilk başarılı frame'i cache'ler, cihaz bazlı warm-up/backoff uygular; health checker TCP erişilebilirlik, latency ve hata nedenini kaydeder. Kalan iyileştirme, FPS/reconnect/uptime gibi daha derin akış kalite metriklerini aynı geçmiş grafiğine bağlamak.
- Vite build kökü açıkça sabitlendi; Windows path çözümleme kaynaklı HTML emit hatası giderildi ve frontend build tekrar kararlı.
- Detection ayarları kısmen kamera bazlı: confidence, IoU, cooldown, aktif saatler ve ROI/poligon eklendi. Kalan iş frame stride ve düşük çözünürlüklü AI örnekleme ayarlarını operatör kontrollü hale getirmek.
- Sadece insan tespiti var: hareket tespiti, çizgi ihlali, bölgeye giriş/çıkış, loitering, kalabalık, kamera sabotajı gibi kural tipleri modüler hale getirilmeli.
- Tracking yok: aynı kişinin ardışık frame'lerde tek olay olarak izlenmesi için tracker ve event aggregation eklenmeli.
- False positive yönetimi başladı: alarm tek tuşla "yanlış alarm" olarak kapatılabiliyor ve DB/audit kaydı oluşuyor. Kalan iş örnekleri eğitim/threshold iyileştirme havuzuna bağlamak.
- AI performans ekranı yok: inference süresi, provider, CPU/GPU kullanımı ve stream başına FPS izlenmeli.

### P1 - Güvenlik ve Operasyon

- WebSocket artık ana JWT yerine kısa ömürlü kamera bazlı stream token kullanıyor. Kalan risk: token hâlâ query string içinde taşındığı için production loglarında query parametreleri maskelenmeli veya ileride handshake tabanlı aktarım değerlendirilmeli.
- HTTPS/TLS, secure cookie, token refresh/expiry UX ve oturum süresi yönetimi eksik.
- Kamera/NVR şifre rotasyonu ve parola değiştirme akışı tamamlanmalı.
- RBAC daha granüler olmalı: canlı izleme, kayıt izleme, export, kullanıcı yönetimi, PTZ, alarm kapatma ayrı izinlere ayrılmalı.
- Backup/restore yok: SQLite DB, config, model ve snapshot/video kayıtlarının yedekleme geri yükleme akışı olmalı.
- Servis/daemon paketleme yok: Windows service veya systemd benzeri üretim çalıştırma, log rotation ve health endpoint derinleştirilmeli.

### P2 - Frontend UX

- Navigasyon dili netleşmeli: `Dashboard` yerine `Canlı İzleme` veya `Kontrol Paneli`; `NVR` yerine `Kayıt Cihazları`; `Settings` route'u yerine `Kullanıcılar`.
- Sidebar sabit genişlikli; küçük ekran/tablet için collapse/drawer davranışı eklenmeli.
- Kameralar, NVR ve Kullanıcılar listelerinde arama/durum/rol gibi hızlı client-side filtreler eklendi. Kalan iş sıralama, sayfalama ve geniş listeler için server-side pagination.
- `confirm()`/`alert()` kullanımı kaldırıldı; kamera, NVR ve kullanıcı silme akışları ortak erişilebilir `ConfirmDialog` modalını kullanıyor. Kalan iş başarılı/başarısız işlemler için toast bildirim standardı.
- Hata mesajları genel: backend `detail` kullanıcıya anlaşılır şekilde gösterilmeli.
- Formlarda password visibility toggle eklendi. Kamera/NVR ekleme akışlarında RTSP path açıklaması ve port sınırları kısmen var. Kamera düzenleme formunda kayıtlı RTSP bağlantı testi doğrudan sunuluyor. Kalan iş kaydedilmemiş form değerleriyle bağlantı önizlemesi ve tüm formlarda doğrulama mesajlarını standartlaştırmak.
- Alarm sayfasında detay drawer, snapshot preview, kamera canlı görüntüsüne geçiş ve toplu onaylama yok.
- Canlı grid'de kamera arama, layout kaydetme, sürükle-bırak sıralama, tam ekran çoklu layout ve düşük bant modu yok.
- Erişilebilirlik eksik: focus ring standardı, klavye navigasyonu, ARIA etiketleri, renk dışı durum göstergeleri, kontrast testi yapılmalı.
- Tema tek koyu palete yaslanıyor; profesyonel operasyon ekranı için daha nötr ve yüksek kontrastlı durum renkleriyle açık/koyu tema seçimi eklenmeli.

### P2 - Teknik Kalite

- Frontend dosya başlığı yorumu kuralı `frontend/src` altında tamamlandı. Kalan iş: backend genelinde tüm module/class/public method docstring kapsamını tamamlamak ve JSDoc kapsamını export bazında sıkılaştırmak.
- Encoding standardı netleştirilmeli: tüm kaynak ve markdown dosyaları UTF-8 olmalı; bozuk karakterler düzeltilmeli.
- Alembic gibi sürümlü migration yapısı yok; script tabanlı migration büyüdükçe riskli olur.
- Test kapsamı yok: domain/use case unit testleri, repository integration testleri, API auth testleri, frontend component testleri eklenmeli.
- API sözleşmesi için OpenAPI export ve frontend tiplerinin otomatik üretimi değerlendirilmeli.
- Frontend code-splitting yapılmalı; route bazlı lazy loading ile build chunk uyarısı düşürülmeli.
- Loglama yapılandırılmalı: hassas veri maskeleme, structured logs, log seviyesi ve dosya rotasyonu.

## Önerilen Yol Haritası

1. P0 operasyon çekirdeği: kayıt, playback, snapshot/export, audit log.
2. AI pipeline ince ayarları: düşük çözünürlüklü AI örnekleme, ROI ve threshold ayarları.
3. RTSP telemetry geçmişi: TCP sağlık geçmişi eklendi; cihaz bazlı açılış süresi, başarısız deneme sayısı, FPS ve stream kalite trendi derinleştirilecek.
3. Alarm detay deneyimi: detay drawer, snapshot preview, not/atanan kişi/çözüm nedeni, önem seviyesi ve yanlış alarm işareti eklendi; sıradaki iyileştirme raporlama/eğitim seti geri beslemesi.
4. Kamera/NVR ekleme sihirbazı: discovery -> test -> profil seç -> import -> izlemeye al.
5. Güvenlik sertleştirme: stream token log maskeleme/handshake iyileştirmesi, refresh flow, izin matrisi, backup/restore.
6. UX temizlik: encoding düzeltme, navigasyon isimleri, responsive sidebar, toast/modal standardı.
7. Test ve üretimleşme: migration sistemi, unit/integration/e2e testler, servis paketleme.

## Doğrulama

- `frontend`: `npm run build` başarılı.
- `backend`: `venv\Scripts\python.exe -m compileall src` başarılı.
