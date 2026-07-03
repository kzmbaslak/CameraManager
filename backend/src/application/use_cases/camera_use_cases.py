from typing import Optional, Sequence
from src.domain.entities.camera import Camera, CameraStatus
from src.domain.interfaces.camera_repository import ICameraRepository


class CameraUseCases:
    """Kamera yönetimi iş mantığını yöneten kullanım senaryosu sınıfı."""

    def __init__(self, camera_repository: ICameraRepository, password_service=None):
        self.camera_repository = camera_repository
        self._password_service = password_service

    def _encrypt_password(self, plain: Optional[str]) -> Optional[str]:
        if plain and self._password_service:
            return self._password_service.encrypt(plain)
        return plain

    def add_camera(
        self,
        name: str,
        host: str,
        rtsp_path: str = "",
        rtsp_port: int = 554,
        onvif_port: int = 80,
        username: Optional[str] = None,
        encrypted_password: Optional[str] = None,
        nvr_id: Optional[int] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
    ) -> Camera:
        if not name or not host:
            raise ValueError("Kamera adı ve sunucu adresi zorunludur.")

        # Aynı IP'ye sahip kamera zaten var mı kontrol et (Upsert mantığı)
        existing_cameras = self.camera_repository.list_all()
        target_host = host.strip().lower()
        existing = None
        
        for cam in existing_cameras:
            if nvr_id is None:
                # Bağımsız kamera: host (IP) eşleşmeli ve NVR'a bağlı olmamalı
                if (
                    cam.nvr_id is None
                    and cam.host
                    and cam.host.strip().lower() == target_host
                    and cam.rtsp_port == rtsp_port
                    and (cam.rtsp_path or "") == (rtsp_path or "")
                ):
                    existing = cam
                    break
            else:
                # NVR kamerası: aynı NVR ve aynı RTSP yolu olmalı
                if (
                    cam.nvr_id == nvr_id
                    and cam.host
                    and cam.host.strip().lower() == target_host
                    and cam.rtsp_port == rtsp_port
                    and (cam.rtsp_path or "") == (rtsp_path or "")
                ):
                    existing = cam
                    break

        if existing:
            # Mevcut kameranın üstüne yaz (Overwrite)
            existing.name = name
            existing.host = host
            existing.rtsp_path = rtsp_path
            existing.rtsp_port = rtsp_port
            existing.onvif_port = onvif_port
            existing.username = username
            if encrypted_password is not None:
                existing.encrypted_password = self._encrypt_password(encrypted_password)
            if brand is not None:
                existing.brand = brand
            if model is not None:
                existing.model = model
            return self.camera_repository.update(existing)

        camera = Camera(
            id=None,
            name=name,
            host=host,
            rtsp_port=rtsp_port,
            onvif_port=onvif_port,
            username=username,
            encrypted_password=self._encrypt_password(encrypted_password),
            rtsp_path=rtsp_path,
            status=CameraStatus.INACTIVE,
            nvr_id=nvr_id,
            brand=brand,
            model=model,
        )
        return self.camera_repository.add(camera)

    def list_cameras(self) -> Sequence[Camera]:
        return self.camera_repository.list_all()

    def get_camera(self, camera_id: int) -> Optional[Camera]:
        return self.camera_repository.get_by_id(camera_id)

    def delete_camera(self, camera_id: int) -> None:
        self.camera_repository.delete(camera_id)

    def update_camera(self, camera: Camera) -> Camera:
        return self.camera_repository.update(camera)

    def update_camera_status(self, camera_id: int, status: CameraStatus) -> Camera:
        camera = self.camera_repository.get_by_id(camera_id)
        if not camera:
            raise ValueError(f"{camera_id} numaralı kamera bulunamadı.")
        camera.status = status
        return self.camera_repository.update(camera)

    def update_camera_ai_detection(self, camera_id: int, enabled: bool) -> Camera:
        """AI insan tespitini açar veya kapatır. Worker yönetimi route katmanında yapılır."""
        camera = self.camera_repository.get_by_id(camera_id)
        if not camera:
            raise ValueError(f"{camera_id} numaralı kamera bulunamadı.")
        camera.ai_detection_enabled = enabled
        return self.camera_repository.update(camera)

    def bulk_add_cameras(self, cameras_list: list) -> list[Camera]:
        """Birden fazla kamerayı toplu olarak sisteme ekler. IP/Host veya NVR kanal çakışması durumunda üzerine yazar (Upsert)."""
        existing_cameras = self.camera_repository.list_all()
        # Bağımsız kayıtlı kameraların IP arama tablosu: {host.strip().lower(): camera_entity}
        existing_standalone = {
            (c.host.strip().lower(), c.rtsp_port, c.rtsp_path or ""): c
            for c in existing_cameras 
            if c.host and c.nvr_id is None
        }
        # NVR'a bağlı kayıtlı kameraların arama tablosu: {(nvr_id, rtsp_path): camera_entity}
        existing_nvr = {
            (c.nvr_id, c.host.strip().lower(), c.rtsp_port, c.rtsp_path or ""): c
            for c in existing_cameras
            if c.nvr_id is not None and c.host
        }

        added_cameras = []
        for cam in cameras_list:
            name = cam.get("name")
            host = cam.get("host")
            rtsp_path = cam.get("rtsp_path", "")
            rtsp_port = cam.get("rtsp_port", 554)
            onvif_port = cam.get("onvif_port", 80)
            username = cam.get("username")
            password = cam.get("password")
            nvr_id = cam.get("nvr_id")
            brand = cam.get("brand")
            model = cam.get("model")
            
            if not name or not host:
                continue
                
            target_host = host.strip().lower()
            
            if nvr_id is None:
                # Bağımsız kamera için IP'ye göre üzerine yaz
                standalone_key = (target_host, rtsp_port, rtsp_path or "")
                if standalone_key in existing_standalone:
                    existing = existing_standalone[standalone_key]
                    existing.name = name
                    existing.rtsp_path = rtsp_path
                    existing.rtsp_port = rtsp_port
                    existing.onvif_port = onvif_port
                    existing.username = username
                    if password is not None:
                        existing.encrypted_password = self._encrypt_password(password)
                    if brand is not None:
                        existing.brand = brand
                    if model is not None:
                        existing.model = model
                    added = self.camera_repository.update(existing)
                    added_cameras.append(added)
                else:
                    camera = Camera(
                        id=None,
                        name=name,
                        host=host,
                        rtsp_port=rtsp_port,
                        onvif_port=onvif_port,
                        username=username,
                        encrypted_password=self._encrypt_password(password),
                        rtsp_path=rtsp_path,
                        status=CameraStatus.INACTIVE,
                        brand=brand,
                        model=model,
                    )
                    added = self.camera_repository.add(camera)
                    existing_standalone[standalone_key] = added
                    added_cameras.append(added)
            else:
                # NVR kamerası için (nvr_id, rtsp_path) bilgisine göre üzerine yaz
                nvr_key = (nvr_id, target_host, rtsp_port, rtsp_path or "")
                if nvr_key in existing_nvr:
                    existing = existing_nvr[nvr_key]
                    existing.name = name
                    existing.host = host
                    existing.rtsp_port = rtsp_port
                    existing.onvif_port = onvif_port
                    existing.username = username
                    if password is not None:
                        existing.encrypted_password = self._encrypt_password(password)
                    if brand is not None:
                        existing.brand = brand
                    if model is not None:
                        existing.model = model
                    added = self.camera_repository.update(existing)
                    added_cameras.append(added)
                else:
                    camera = Camera(
                        id=None,
                        name=name,
                        host=host,
                        rtsp_port=rtsp_port,
                        onvif_port=onvif_port,
                        username=username,
                        encrypted_password=self._encrypt_password(password),
                        rtsp_path=rtsp_path,
                        status=CameraStatus.INACTIVE,
                        nvr_id=nvr_id,
                        brand=brand,
                        model=model,
                    )
                    added = self.camera_repository.add(camera)
                    existing_nvr[nvr_key] = added
                    added_cameras.append(added)
                    
        return added_cameras
