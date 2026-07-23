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
- Kanıt yönetimi kısmen eklendi: alarm snapshot dosyaları detay panelinde görüntülenir, indirilebilir, SHA-256 bütünlük değeriyle gösterilir ve snapshot erişimi audit log'a yazılır. İnsan tespiti alarmlarında ham/adli snapshot ile tüm insan kutuları çizilmiş operatör kanıtı ayrı dosyalar olarak saklanır. Kalan iş video export ve daha kapsamlı kanıt zinciri/raporu üretmek.
- Alarm operasyon akışı büyük ölçüde tamamlandı: yeni/onaylandı/çözüldü, atanan kullanıcı, not, önem seviyesi, olay kapatma nedeni, yanlış alarm işareti ve detay paneli var. Kalan iş bu operasyon verisini raporlama/eğitim seti akışına bağlamak.
- Audit log büyük ölçüde tamamlandı: kullanıcı girişleri, parola değişimi, kamera/NVR değişiklikleri, alarm aksiyonları ve snapshot erişimi JSONL audit log'a yazılıyor; admin kullanıcılar Sistem ve Kullanıcılar ekranında son olayları görebiliyor, metin/durum filtresiyle inceleyebiliyor ve görünen sonucu CSV olarak dışa aktarabiliyor. Dosya boyutu ve gün bazlı retention politikası `AUDIT_MAX_BYTES` / `AUDIT_RETENTION_DAYS` ile eklendi. Yeni olaylar zincirli hash ile yazılır; `AUDIT_CHAIN_SECRET` varsa HMAC-SHA256 kullanılır. `AUDIT_WEBHOOK_URL` ile merkezi/SIEM arşivine opsiyonel gönderim var. Kalan iş kurum SIEM tarafında endpoint, TLS ve saklama politikasını operasyonel olarak devreye almak.
- İlk kurulum akışı kısmen var: otomatik varsayılan admin kaldırıldı, env kontrollü ilk admin ve CLI seed scripti var. `.env`, model dosyası, DB şeması ve aktif admin varlığı preflight kontrolüyle `/api/setup/status` ve güvenlik duruşu içinde raporlanıyor. Kalan iş kamera/NVR ekleme sihirbazını tek akışa bağlamak.

### P1 - Kamera/NVR Yönetimi

- ONVIF yetenek keşfi kısmen var: NVR kanal keşfi ve kamera formunda kaydetmeden GetDeviceInformation/stream URI profil testi çalışıyor. Kalan iş Profile S/T/G/M uyumluluk bilgisi, çözünürlük/FPS/codec, snapshot URI, event subscriptions ve PTZ capability alanlarını ayrıntılı okumak.
- PTZ desteği yok: pan/tilt/zoom, preset, patrol ve yetkiye bağlı PTZ kontrolü eklenmeli.
- Kamera sağlık metrikleri yetersiz: son frame zamanı, reconnect sayısı, FPS, latency, hata nedeni ve uptime gösterilmeli.
- NVR import deneyimi geliştirilmeli: daha önce eklenen kanallar işaretlenmeli, kanal ismi düzenlenebilmeli, toplu profil seçimi ve duplicate raporu sunulmalı.
- Kamera bağlantı testi büyük ölçüde tamamlandı: kamera listesinde kayıtlı RTSP bağlantısı; kamera ekleme ve düzenleme modallarında kaydetmeden RTSP TCP/DESCRIBE/frame ve ONVIF cihaz/profil testi açıklayıcı sonuçlarla çalışıyor. Düzenleme formunda yeni şifre boşsa backend kayıtlı şifreyi güvenli şekilde kullanıyor. Kalan iş ONVIF capability detaylarını aynı sonuç paneline genişletmek.
- Çoklu saha/konum modeli yok: site, bina, kat, bölge gibi hiyerarşi ve ileride harita/floorplan görünümü için domain alanları eklenmeli.

### P1 - AI ve Olay Tespiti

- AI pipeline ayrıştırıldı: canlı yayın capture hattı artık ayrı çalışıyor, AI tespiti ise arka planda bağımsız görev olarak tetikleniyor. Kamera bazlı frame stride ve düşük çözünürlüklü AI örnekleme ayarları eklendi; bounding box koordinatları orijinal kareye geri ölçekleniyor. Kalan iş bu ayarları otomatik yük/adaptif kalite politikasına bağlamak.
- RTSP açılış optimizasyonu ve kalıcı sağlık geçmişi eklendi: `OpenCVStreamReader` ilk başarılı frame'i cache'ler, cihaz bazlı warm-up/backoff uygular; health checker TCP erişilebilirlik, latency ve hata nedenini kaydeder. Kalan iyileştirme, FPS/reconnect/uptime gibi daha derin akış kalite metriklerini aynı geçmiş grafiğine bağlamak.
- Vite build kökü açıkça sabitlendi; Windows path çözümleme kaynaklı HTML emit hatası giderildi ve frontend build tekrar kararlı.
- Detection ayarları kamera bazlı: confidence, IoU, cooldown, frame stride, AI örnekleme genişliği, aktif saatler ve ROI/poligon operatör kontrollü hale geldi. Kalan iş bu ayarları toplu şablon/preset yönetimine bağlamak.
- Sadece insan tespiti var: hareket tespiti, çizgi ihlali, bölgeye giriş/çıkış, loitering, kalabalık, kamera sabotajı gibi kural tipleri modüler hale getirilmeli.
- Tracking yok: aynı kişinin ardışık frame'lerde tek olay olarak izlenmesi için tracker ve event aggregation eklenmeli.
- False positive yönetimi başladı: alarm tek tuşla "yanlış alarm" olarak kapatılabiliyor ve DB/audit kaydı oluşuyor. Kalan iş örnekleri eğitim/threshold iyileştirme havuzuna bağlamak.
- AI performans görünürlüğü kısmen var: kamera stream telemetrisinde AI provider, frame stride ve örnekleme genişliği gösteriliyor. Kalan iş inference süresi, CPU/GPU kullanımı ve stream başına FPS trendini kalıcı metrik olarak izlemek.

### P1 - Güvenlik ve Operasyon

- WebSocket artık ana JWT yerine kısa ömürlü kamera bazlı stream token kullanıyor ve token URL query yerine ilk WebSocket mesajında taşınıyor. Kalan risk: production proxy loglarında `/api/streams/{camera_id}?profile=...` gibi hassas olmayan query parametreleri yine de standart log maskesiyle yönetilmeli.
- HTTPS/TLS, secure cookie ve token refresh eksik. Frontend tarafinda JWT expiry UX eklendi: sure dolmadan operator uyarilir, suresi dolmus token istek oncesi temizlenir ve login ekraninda oturum suresi mesaji gosterilir.
- Kamera/NVR şifre rotasyonu ve parola değiştirme akışı tamamlanmalı.
- RBAC daha granüler olmalı: canlı izleme, kayıt izleme, export, kullanıcı yönetimi, PTZ, alarm kapatma ayrı izinlere ayrılmalı.
- Backup/restore kısmen eklendi: SQLite DB, `.env`, `backend/data`, YOLO modeli ve snapshot dosyaları SHA-256 manifestli zip arşivine alınabiliyor; restore script'i manifest/hash doğrulaması, path sınırı, `--dry-run` ve `--force` koruması kullanıyor. Kalan iş bunu admin arayüzüne, zamanlanmış yedekleme politikasına ve ileride video kayıt klasörlerine bağlamak.
- Servis/daemon paketleme yok: Windows service veya systemd benzeri üretim çalıştırma, log rotation ve health endpoint derinleştirilmeli.

### P2 - Frontend UX

- Navigasyon dili netleşti: `Dashboard` yerine `Canli Izleme`, `NVR` yerine `Kayit Cihazlari`, ayarlar/kullanıcı alanı için `Sistem ve Kullanicilar` kullanılıyor. `/recorders` ve `/users` route'ları eklendi; eski `/nvr` ve `/settings` adresleri geriye uyumlu yönlenir.
- Sidebar desktop'ta sabit, küçük ekran/tablet için üst bar ve overlay drawer davranışı eklendi. Kalan iş ileri seviye kullanıcı tercihi olarak desktop collapse durumunu kalıcı saklamak.
- Kameralar, NVR ve Kullanıcılar listelerinde arama/durum/rol gibi hızlı filtreler ve ad/durum/aktiflik/host/rol/en yeni gibi sıralama kontrolleri backend query parametrelerine bağlandı; `paginated=true` ile server-side pagination, sayfa boyutu seçimi ve toplam sonuç sayacı eklendi.
- `confirm()`/`alert()` kullanımı kaldırıldı; kamera, NVR ve kullanıcı silme akışları ortak erişilebilir `ConfirmDialog` modalını kullanıyor. Global toast standardı eklendi ve kamera/NVR/kullanıcı/alarm operasyonlarına başarı/başarısızlık bildirimleri bağlandı. Ortak API hata mesajı yardımcı fonksiyonu ile kamera, NVR, kullanıcı ve alarm hataları backend `detail` veya okunabilir fallback mesajını gösteriyor. Kamera/NVR/kullanıcı ekleme ve düzenleme formlarında alan bazlı inline validasyon eklendi; kalan iş tarama/import gibi çok satırlı özel akışlarda satır bazlı validasyon kapsamını genişletmek.
- Formlarda password visibility toggle eklendi. Kamera/NVR ekleme akışlarında RTSP path açıklaması ve port sınırları var. Kamera ekleme/düzenleme formlarında kaydetmeden RTSP ve ONVIF bağlantı önizlemesi sunuluyor. Ortak alan bazlı form doğrulama yardımcısı kamera/NVR/kullanıcı yönetim formlarında kullanılıyor.
- Alarm sayfasında detay drawer, snapshot preview, kamera canlı görüntüsüne geçiş, toplu onaylama, not/atama/çözüm nedeni, önem seviyesi ve yanlış alarm kapatma akışları eklendi. Kalan iş bu verileri raporlama/eğitim seti geri beslemesine bağlamak.
- Canlı grid'de kamera arama, layout kalıcılığı, düşük bant modu, sürükle-bırak kamera sıralaması ve tam ekran 1/2x2/3x3 çoklu layout eklendi. Kalan iş daha ileri seviye layout preset paylaşımı ve rol bazlı layout şablonları.
- Erişilebilirlik kısmen iyileştirildi: global focus ring var; ortak Input hata metnini ARIA ile input'a bağlar, Modal dialog semantiği taşır, Button varsayılan submit riskini azaltır ve Table ekran okuyucu caption/bos durum desteği alır. Kalan iş sayfa bazlı klavye gezinme denetimi, kontrast testi ve tüm özel kontrol gruplarında ARIA etiketlerini tamamlamak.
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

- `frontend`: `npm run lint` ve `npm run build` başarılı.
- `backend`: `venv\Scripts\python.exe -m compileall src` başarılı.
