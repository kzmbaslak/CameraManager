# Kurallar ve Yönergeler (Rules and Guidelines)

## 1. Kesin Çevrimdışı (Offline) Kuralı
- Sistem internete dışa doğru (outbound) hiçbir istek **yapmamalıdır**.
- Bulut (cloud) loglaması veya telemetri olmamalıdır (örneğin, YOLO telemetrisi `YOLO_OFFLINE=True` ve `WANDB_DISABLED=True` ile devre dışı bırakılmalıdır).
- Tüm modeller, bağımlılıklar (dependencies) ve ön uç (frontend) dosyaları yerel (local) olmalıdır.

## 2. SOLID Prensipleri
- **Tek Sorumluluk (Single Responsibility):** Her sınıf/modül sadece tek bir iş yapmalıdır. (Örn: RTSP okuma işlemi ile yapay zeka (AI) çıkarımı ayrıdır).
- **Açık/Kapalı (Open/Closed):** Mevcut kodu değiştirmeden yeni özellikler (yeni bir AI modeli gibi) eklenebilmesi için arayüzler (interfaces) kullanın.
- **Liskov Yerine Geçme (Liskov Substitution):** Altyapı (Infrastructure) uygulamaları, Alan (Domain) arayüzlerini tam olarak takip etmelidir.
- **Arayüz Ayrımı (Interface Segregation):** Arayüzleri (interfaces) küçük ve spesifik tutun.
- **Bağımlılığın Tersine Çevrilmesi (Dependency Inversion):** Üst düzey modüller (Application), alt düzey uygulamalara (Infrastructure) değil, soyutlamalara (Domain Interfaces) bağımlı olmalıdır. Bağımlılık Enjeksiyonu (Dependency Injection) kullanın (FastAPI Depends aracılığıyla veya `main.py` içinde manuel olarak).

## 3. Güvenlik (Security)
- Kamera kimlik bilgileri (şifreler), veritabanında saklanmadan önce AES-256 kullanılarak şifrelenmelidir (encrypted).
- Hassas URL'leri veya şifreleri düz metin (plain text) olarak loglamayın.
- API'ler temel JWT veya Rol Tabanlı erişim (Admin, Operatör, İzleyici) ile güvence altına alınmalıdır.

## 4. Türkçe Açıklama ve Dokümantasyon Kuralı (Turkish Comment & Documentation Rule)
- Kod içerisindeki **tüm açıklamalar (comments) Türkçe** olmalıdır.
- Kullanılan sınıf/değişken isimleri İngilizce kalsa bile, ne işe yaradıkları Türkçe açıklanacaktır.
- `BoundingBox`, `Detection` gibi teknik kod isimlendirmeleri (tanım/kısaltmalar) orijinal İngilizce halleriyle bırakılacak, ancak açıklamaları hem İngilizce hem Türkçe terimleri içerecek şekilde yapılacaktır (Örn: `BoundingBox (Sınırlayıcı Kutu)`).
- Tüm dokümantasyon dosyaları (Markdown) aynı şekilde Türkçe/İngilizce çift dilli formata uygun olarak oluşturulmalıdır.

## 5. UX ve Arayüz Tasarımı Kuralları (UX & Interface Design Rules)

> Claude Code bu projede hem geliştirici hem de web tasarımcısı rolünü üstlenir. Kod yazarken aşağıdaki UX prensiplerini daima gözetmelidir.

### 5.1 Etiket Netliği (Label Clarity)
- Buton ve eylem etiketleri **etkiyi** tarif etmeli, eylemi değil.
  - ✗ "Başlat" / "Durdur" — neyi başlatıyor?
  - ✓ "İzlemeye Al" / "İzlemeyi Durdur" — sisteme etkisi net
- Her butonun `title` (tooltip) özelliği, arka planda ne olduğunu tek cümleyle açıklamalıdır.
- Durum sütunlarına mikro açıklama (`10px` alt metin) eklenmelidir: `"Sistem bu kamerayı izliyor"`.

### 5.2 Kullanıcı İş Akışı (User Workflow)
- Kullanıcının bir sayfada başladığı işi (ör. NVR tarama → NVR ekleme) ayrı sayfaya geçmeden tamamlayabilmesi için **modal zinciri** kurulmalıdır.
- Keşif sonuçları (discover, probe) doğrudan ekleme formunu önceden doldurmalıdır (prefill).
- Sık kullanılan işlemler ana sayfada görünür olmalı; nadiren kullanılanlar modal veya alt panelde gizlenmelidir.

### 5.3 Navigasyon İsimlendirmesi (Navigation Naming)
- Sayfa adları İngilizce teknik terim değil, **kullanıcının ne yapacağını** anlatan Türkçe olmalıdır.
  - ✗ "Settings" / "Ayarlar" (tek başına belirsiz)
  - ✓ "Kullanıcılar" — içeriği doğrudan tarif eder
- Sidebar ikonları içeriğe semantik olarak uygun olmalıdır (ör. Users → Users2 ikonu).

### 5.4 Toplu İşlem ve Seçim (Bulk Actions & Selection)
- Birden fazla öğe içe aktarılabilecek listelerde (ör. NVR kanalları) mutlaka checkbox seçimi ve **"Seçilenleri Ekle"** butonu bulunmalıdır.
- "Tümünü Seç" / "Tümünü Kaldır" kısayolu her listede olmalıdır.
- Aktarma öncesinde seçili sayı kullanıcıya gösterilmelidir: `"3 / 8 kanal seçili"`.

### 5.5 Filtreleme Standardı (Filtering Standard)
- Liste sayfaları (Alarmlar, Kameralar, vs.) mutlaka filtreleme desteklemelidir:
  - **Backend filtresi:** Büyük veri setleri için (kamera_id, tip, durum) → API parametresi olarak gönderilmeli.
  - **Client-side filtresi:** Küçük/hızlı filtreler (tarih aralığı, arama metni) → frontend'de `useMemo` ile uygulanmalı.
- Aktif filtre olduğunda başlık alanında `"· Filtre aktif"` göstergesi olmalıdır.
- Her filtre kombinasyonu kolayca sıfırlanabilmeli: **"Sıfırla"** butonu.

### 5.6 Backend Senkronizasyonu (Backend Sync)
- Frontend'e eklenen her yeni özellik için backend endpoint'inin varlığı doğrulanmalıdır.
- Yeni endpoint gerektiren frontend değişikliği commit'i, backend değişikliğini de aynı commit'e içermelidir.

---

## 6. Dosya ve Fonksiyon Açıklama Zorunluluğu (File & Function Documentation Rule)

### Backend (Python)
- Her `.py` dosyasının en üstünde **modül docstring** bulunmalıdır: dosyanın ne yaptığı, hangi endpoint'leri veya sınıfları içerdiği.
- Her sınıf ve public metot için **docstring** yazılmalıdır.
- Format: `"""Türkçe açıklama."""`

### Frontend (TypeScript / React)
- Her `.ts` / `.tsx` dosyasının **ilk satırında** dosyanın amacını açıklayan bir Türkçe yorum bulunmalıdır:
  ```ts
  // Kamera CRUD API çağrıları — list, get, add, updateStatus, toggleAI, delete
  ```
- Her **export edilen fonksiyon, hook, bileşen ve store**'un üzerinde kısa bir Türkçe JSDoc yazılmalıdır:
  ```ts
  /** Kamera AI tespitini açar veya kapatır; worker yönetimini tetikler. */
  toggleAI: async (id, enabled) => { ... }
  ```
- Inline mantık açıklaması: `// neden` formatında, `// ne` değil (iyi isimlendirme "ne"yi zaten anlatır).
- Bu kural **tüm yeni ve mevcut** frontend ile backend dosyalarına uygulanacaktır.
