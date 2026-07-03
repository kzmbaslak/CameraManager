# Kamera/NVR Bağlantı İnceleme Notları

## Sorun Özeti

- NVR sisteme kaydedilebiliyor, fakat NVR üzerinden taranıp eklenen kameralar bazen ulaşılamaz hale geliyordu.
- Manuel kamera eklemede bazı cihazlar eklenemiyor veya doğru RTSP yolu bulunamıyordu.
- Illustra/i610 gibi eski cihazlarda web arayüzü tarayıcı/Windows kimlik doğrulama penceresine düşebiliyor.
- Bazı kameralar yanlış şifre girilse bile izlenebiliyor; VLC'de de şifresiz erişilebilen cihazlar aynı şekilde görüntü verebiliyor.

## Tespitler

- NVR import sırasında ONVIF/RTSP kanal URL'sindeki gerçek host/port/path/kullanıcı bilgisi korunmuyordu; kayıt sırasında kamera host'u her zaman NVR host'u yapılıyordu.
- Manuel kamera ekleme bağlantı doğrulaması yapmadan kayıt oluşturuyordu.
- RTSP tarama sadece ham `DESCRIBE` kontrolüne dayanıyordu; bazı Basic/Digest davranışı farklı eski cihazlarda gerçek frame okunabildiği halde tarama başarısız olabiliyordu.
- Kamera upsert anahtarı bağımsız kameralarda sadece host'a, NVR kanallarında ise sadece `(nvr_id, rtsp_path)` değerine fazla yakın davranıyordu; farklı port/path/host kombinasyonları birbirini ezebiliyordu.
- Yanlış şifreyle izlenebilen cihazlarda cihaz RTSP stream'i anonim erişime açıyor olabilir. VLC de şifresiz görüntü alabiliyorsa bu uygulama hatası değil, cihaz/NVR tarafında anonim RTSP erişimi veya cached/guest stream davranışıdır.

## Yapılan Düzeltmeler

- Illustra i610 için VLC'de doğrulanan `/primarystream` RTSP yolu bilinen path listesinde önceliklendirildi; kullanıcı arayüzünde 7778 portu ve `/primarystream` bilgisi görünür hale getirildi.
- Kamera ekleme ve kamera tarama ekranlarına isteğe bağlı alternatif RTSP port denemesi eklendi. Kullanıcı açarsa seçili porttan sonra 554, 8554, 10554, 7070, 7777 ve 7778 denenir; bulunan gerçek port kamera kaydına yazılır.
- Kamera taramada eski cihazların port ön kontrolünde elenmemesi için RTSP path denemeleri doğrudan yapılır.
- Kamera ekleme ve kamera tarama RTSP doğrulamaları zaman sınırıyla çalışacak şekilde düzenlendi; OpenCV/FFmpeg fallback artık sınırsız bekleyip frontend'de belirsiz "Network Error" üretmez.
- NVR kanal import'u kaydetmeden önce erişilebilen RTSP endpoint'i seçiyor: önce ONVIF'in döndürdüğü host, sonra aynı path ile NVR host'u deneniyor. Hiçbiri çalışmazsa kanal bozuk kaydedilmiyor ve kullanıcıya doğrulama hatası dönüyor.
- NVR kanal import'u artık sadece RTSP DESCRIBE cevabıyla yetinmez; gerçek frame okunabilen endpoint'i kaydeder.
- NVR kanal import'u ONVIF'in verdiği URL çalışmazsa kanal numarasını path/profil bilgisinden tahmin ederek NVR host'u üzerinde VideoEdge, Hikvision, Dahua ve genel kanal şablonlarını 554, 8554, 10554 ve 7778 portlarında gerçek frame okuyarak dener. Hata durumunda denenen adayları DESCRIBE/Auth Frame/Anon Frame sonucuyla döndürür.
- Kameralar ekranına "Test Et" eylemi eklendi; kayıtlı kameranın TCP, RTSP DESCRIBE ve gerçek frame okuma sonucu şifre göstermeden raporlanır.
- RTSP frame okuma ve canlı izleme tarafına anonim fallback eklendi. Kimlik bilgili URL frame vermez ama aynı host/port/path anonim çalışırsa sistem anonim stream ile görüntü alır; tanı ekranı Auth Frame ve Anon Frame sonucunu ayrı gösterir.
- OpenCV/FFmpeg frame okuma artık tek başına TCP transport'a zorlanmaz; varsayılan, UDP ve TCP profilleri gerçek frame okuyana kadar denenir. VLC'de açılıp sistemde frame vermeyen eski RTSP cihazları için bu fark kritik olabilir.
- Kamera tarama alanı artık tekil hostname değerlerini de kabul eder; sadece IP/CIDR aralığıyla sınırlı değildir.
- NVR import aday listesi ve timeout'ları kısaltıldı; DESCRIBE alamayan adaylarda pahalı frame okuma atlanır ve frontend HTTP timeout'u uzun NVR işlemleri için 300 saniyeye çıkarıldı.
- `ONVIFProbeService.parse_rtsp_endpoint()` eklendi; tam RTSP URL artık host, port, path, kullanıcı ve şifre alanlarına ayrılıyor.
- NVR import, kanalın döndürdüğü gerçek RTSP endpoint'ini kaydediyor; NVR host'unu körlemesine kamera host'u olarak yazmıyor.
- `camera_scanner.py` içinde OpenCV/FFmpeg ile gerçek frame okuma doğrulaması eklendi.
- Manuel kamera ekleme:
  - Boş RTSP path verilirse bilinen path listesi deneniyor.
  - Tam `rtsp://...` URL verilirse alanlar ayrıştırılıyor.
  - Path verilmişse kayıt öncesi RTSP erişimi doğrulanıyor.
- `OpenCVStreamReader` slash'sız path değerlerini normalize ediyor.
- Kamera upsert anahtarı host + RTSP port + path, NVR kanalları için NVR + host + RTSP port + path olarak daraltıldı.
- Frontend kamera ekleme ekranında RTSP path/Illustra/i610 yönlendirmesi ve backend hata detayları görünür hale getirildi.
- Frontend kamera/NVR tarama ekranlarında gerçek frame doğrulaması, anonim RTSP uyarısı, kanal URL görünürlüğü ve inline import/hata mesajları eklendi.

## Doğrulama

- Backend derleme: `venv\Scripts\python.exe -m compileall src` başarılı.
- FastAPI import kontrolü: `venv\Scripts\python.exe -c "from main import app; print(app.title)"` başarılı.
- Frontend build çalıştırılamadı; bu oturumda `node`, `npm` ve `npm.cmd` PATH'te bulunamadı.

## Operasyon Notu

Müşteri paketi oluşturulurken `backend/data/rtsp_paths.json` dosyası paket içindeki `backend/data/` klasörüne kopyalanmalıdır. Paketleme scripti artık dosya eksikse veya kaynak/hedef SHA-256 değerleri farklıysa işlemi hata ile durdurur. Daha önce üretilmiş paketler bu kontrolü içermez; `Musteri_Paketle.bat` yeniden çalıştırılmalıdır.

VideoEdge/NVR tarafında `DESCRIBE=OK`, video frame'in gerçekten geldiği anlamına gelmez. VLC ve OpenCV aynı NVR endpoint'inde bağlantı kurup görüntü alamıyorsa endpoint kamera olarak kaydedilmez. `%21`, RTSP URL içindeki `!` karakterinin standart encode edilmiş gösterimidir; endpoint parse edilirken tekrar `!` değerine çevrilir. Console loglarında kimlik bilgili RTSP URL'lerin şifresi maskelenir.

Illustra/i610 ve benzeri cihazlarda önce şu yollar denenmeli:

- `/videoStreamId=1`
- `/stream1`
- `/ufirststream`
- `/primarystream`
- `/primarystream` (i610 cihazlarda 7778 portu ile doğrulandı)

Eğer VLC şifresiz görüntü alabiliyorsa cihazın RTSP anonim erişimi kapatılmalı veya kamera/NVR üzerinde yalnızca kimlik doğrulamalı stream profili kullanılmalıdır.
