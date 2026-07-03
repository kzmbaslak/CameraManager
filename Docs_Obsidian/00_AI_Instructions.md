# Yapay Zeka (AI) Asistanı İletişim Protokolü ve Talimatları (AI Assistant Communication Protocol & Instructions)

**TÜM YAPAY ZEKA ASİSTANLARI İÇİN KRİTİK TALİMAT (CRITICAL INSTRUCTION FOR ALL AI ASSISTANTS):**
Bu projede herhangi bir değişiklik yapmadan önce, projenin mimarisini, kesin kurallarını (çevrimdışı/offline, yerel/local, NVR'dan bağımsız) ve mevcut ilerleme durumunu anlamak için `Docs_Obsidian` dizinindeki dosyaları **OKUMALISINIZ**.

## Yapay Zeka Asistanları İçin Kurallar (Rules for AI Assistants)
1. **Önce Oku (Read First):** Önceki yapay zekanın nerede kaldığını görmek için her zaman `03_Current_State.md` dosyasını kontrol edin.
2. **Mimariye Uy (Follow Architecture):** 4 katmanlı DDD (Domain-Driven Design) mimarisini anlamak için `01_Project_Overview_and_Architecture.md` dosyasına başvurun. İş mantığını (business logic) yönlendiricilere (routes) veya veritabanı mantığını (DB logic) uygulama (application) katmanına koyarak bu mimariyi ASLA bozmayın.
3. **Durumu Güncelle (Update State):** Bir görevi tamamladığınızda veya oturumunuzu durdurduğunuzda, bir sonraki AI'ın (veya insanın) ne yapıldığını ve sırada ne olduğunu tam olarak bilmesi için `03_Current_State.md` dosyasını **GÜNCELLEMELİSİNİZ**.
4. **Çalışmanı Kaydet (Commit Your Work):** Her AI asistanı, oturumu sonlandırmadan önce kendi tamamladığı değişiklikleri net bir commit mesajıyla git'e **KAYDETMELİDİR (COMMIT YAPMALIDIR)**.
5. **Kılavuzlara Uy (Adhere to Guidelines):** Kodlama standartları, SOLID prensipleri ve katı güvenlik/çevrimdışı (offline) kısıtlamaları için her zaman `02_Rules_and_Guidelines.md` dosyasına bakın.
6. **Türkçe Yorum Kuralları (Turkish Comment Rules):** Kod içerisindeki tüm açıklamalar (comments) Türkçe olmalıdır. BoundingBox gibi kodda yer alan terimler orijinal İngilizce adlarıyla bırakılmalı, ancak tanımları ve kısaltmaları hem İngilizce hem de Türkçe olacak şekilde açıklanmalıdır.

Bu talimatları anladıysanız, lütfen bu klasördeki diğer belgeleri okumaya devam edin ve onlara kesinlikle uyun.
