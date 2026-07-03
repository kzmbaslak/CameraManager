"""
NVR (Network Video Recorder) Pydantic şemaları.

Bu modüldeki sınıflar, NVR API endpoint'lerinin istek (request)
ve yanıt (response) veri yapılarını tanımlar.
"""
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class NVRCreate(BaseModel):
    """
    Yeni NVR cihazı eklemek için kullanıcıdan alınan veriler.
    Şifre burada düz metin olarak gelir; servis katmanında AES-256 ile şifrelenerek
    veritabanına kaydedilir.
    """
    name: str                          # Tanımlayıcı isim (örn: "Giriş Katı NVR")
    host: str                          # IP adresi veya hostname
    onvif_port: int = 80               # ONVIF yönetim portu (genellikle 80 veya 8080)
    username: Optional[str] = None     # ONVIF kullanıcı adı
    password: Optional[str] = None     # Düz metin şifre — kaydedilmez, şifrelenir
    brand: Optional[str] = None        # NVR markası (örn: VideoEdge)
    model: Optional[str] = None        # NVR modeli


class NVRResponse(BaseModel):
    """
    API'nin NVR bilgisi dönerken kullandığı yanıt modeli.
    Şifre hiçbir zaman döndürülmez.
    """
    id: int
    name: str
    host: str
    onvif_port: int
    username: Optional[str] = None
    brand: Optional[str] = None        # ONVIF'ten otomatik alınan marka
    model: Optional[str] = None        # ONVIF'ten otomatik alınan model
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class NVRUpdate(BaseModel):
    """NVR cihazını kısmi olarak güncellemek için kullanılan istek modeli. None alanlar değiştirilmez."""
    name: Optional[str] = None
    host: Optional[str] = None
    onvif_port: Optional[int] = None
    username: Optional[str] = None
    password: Optional[str] = None   # None → şifre değiştirilmez


class NVRProbeRequest(BaseModel):
    """
    NVR kanallarını sorgulamak için kullanılan istek modeli.
    nvr_id URL parametresiyle geldiğinden bu şema şu an kullanılmıyor;
    ileride kimlik bilgisi override için ayrılmıştır.
    """
    onvif_port: Optional[int] = None   # None ise kayıtlı port kullanılır


class NVRChannelInfo(BaseModel):
    """
    NVR'dan ONVIF ile okunan bir kamera kanalının önizleme bilgileri.
    Sisteme kaydetmeden önce kullanıcıya gösterilir.
    """
    profile_token: str              # ONVIF profil token'ı (her kanal benzersiz)
    profile_name: str               # Kanal adı (örn: "MainStream", "Kanal-1")
    manufacturer: Optional[str] = None   # Cihaz markası
    model: Optional[str] = None         # Cihaz modeli
    rtsp_url: str                   # NVR üzerinden tam RTSP adresi


class NVRDiscoverResponse(BaseModel):
    """
    WS-Discovery ile ağda bulunan bir ONVIF cihazının bilgileri.
    """
    xaddr: str
    host: str
    port: int


class NVRImportRequest(BaseModel):
    """
    Seçili ONVIF/RTSP kanallarını içe aktarmak için kullanılan istek modeli.
    """
    channels: List[NVRChannelInfo]


class NVRScanRequest(BaseModel):
    ip_range: str
    rtsp_port: Optional[int] = 554
    username: Optional[str] = None
    password: Optional[str] = None


class NVRScanResponse(BaseModel):
    host: str
    port: int
    brand: str
    model: str


