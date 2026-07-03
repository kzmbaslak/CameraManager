import os
import cv2
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from src.domain.entities.camera import CameraStatus
from src.domain.entities.alarm import Alarm, AlarmType, AlarmStatus, BoundingBox
from src.domain.interfaces.camera_repository import ICameraRepository
from src.domain.interfaces.alarm_repository import IAlarmRepository
from src.domain.interfaces.frame_source import IFrameSource
from src.domain.interfaces.ai_inference_service import IAIInferenceService

class ProcessFrameUseCase:
    """Görüntü okuma, yapay zeka analizine sokma ve alarm oluşturma iş akışını yöneten sınıf."""
    
    def __init__(
        self,
        camera_repository: ICameraRepository,
        alarm_repository: IAlarmRepository,
        frame_source: IFrameSource,
        ai_service: IAIInferenceService,
        snapshot_dir: str = "snapshots",
        cooldown_seconds: int = 60
    ):
        self.camera_repository = camera_repository
        self.alarm_repository = alarm_repository
        self.frame_source = frame_source
        self.ai_service = ai_service
        self.snapshot_dir = snapshot_dir
        self.cooldown_seconds = cooldown_seconds
        
        # Kamera ID ve Alarm Tipine göre son tetiklenme zamanını tutar (Stores last trigger time per Camera ID and Alarm Type)
        # Format: {(camera_id, alarm_type): datetime}
        self._last_alarms: Dict[Tuple[int, AlarmType], datetime] = {}
        
        # Anlık Görüntü (Snapshots) dizinini oluştur
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def _is_in_cooldown(self, camera_id: int, alarm_type: AlarmType) -> bool:
        """Belirtilen kamera ve alarm türü için bekleme süresinin (cooldown) geçip geçmediğini kontrol eder."""
        key = (camera_id, alarm_type)
        if key in self._last_alarms:
            time_since_last = datetime.utcnow() - self._last_alarms[key]
            if time_since_last < timedelta(seconds=self.cooldown_seconds):
                return True # Hala bekleme süresinde (Still in cooldown)
        return False

    def _save_snapshot(self, frame: object, camera_id: int, bounding_box: Optional[BoundingBox] = None) -> str:
        """Görüntüyü diske kaydeder ve dosya yolunu döndürür."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"cam_{camera_id}_{timestamp}.jpg"
        filepath = os.path.join(self.snapshot_dir, filename)
        
        # Eğer BoundingBox (Sınırlayıcı Kutu) varsa görüntü üzerine çiz (Draw bounding box on frame if present)
        save_frame = frame.copy()
        if bounding_box:
            x1, y1 = bounding_box.x, bounding_box.y
            x2, y2 = x1 + bounding_box.width, y1 + bounding_box.height
            cv2.rectangle(save_frame, (x1, y1), (x2, y2), (0, 0, 255), 2) # Kırmızı kutu (Red box)
            
        cv2.imwrite(filepath, save_frame)
        return filepath

    def read_frame(self, camera_id: int, camera=None) -> Optional[object]:
        """Kameradan tek bir kare okur ve durumunu (active/error) günceller.

        AI açık/kapalı ayrımı yapmaz — canlı izleme görüntüsü için de kullanılır.
        Kamera bulunamazsa veya kare okunamazsa None döner.

        `camera` parametresi verilirse DB sorgusu atlanır (üretici döngüsünde
        çift sorguyu önler).
        """
        if camera is None:
            camera = self.camera_repository.get_by_id(camera_id)
        if not camera:
            return None

        frame = self.frame_source.read_frame(camera)
        if frame is None:
            if camera.status != CameraStatus.ERROR:
                camera.mark_error()
                self.camera_repository.update(camera)
            return None

        if camera.status == CameraStatus.ERROR:
            camera.activate()
            self.camera_repository.update(camera)
            # Kamera gerçek frame okuyarak toparlıyor — CAMERA_OFFLINE alarmlarını çöz
            for a in self.alarm_repository.list_by_camera(camera.id):
                if a.alarm_type == AlarmType.CAMERA_OFFLINE and a.status != AlarmStatus.RESOLVED:
                    a.resolve(datetime.utcnow())
                    self.alarm_repository.update(a)

        return frame

    def detect_and_alarm(self, camera_id: int, frame: object) -> Optional[Alarm]:
        """Verilen kare üzerinde AI tespiti çalıştırır; eşik ve cooldown'a göre alarm üretir.

        Not: CAMERA_OFFLINE alarmı burada ÜRETİLMEZ — bu sorumluluk tamamen
        CameraHealthChecker'a aittir (tek kaynak, kalıcı cooldown).
        """
        detections = self.ai_service.detect_humans(frame)

        if detections:
            # En yüksek güven (confidence) skoruna sahip tespiti al
            best_detection = max(detections, key=lambda d: d.confidence)
            
            # Bekleme süresi (Cooldown) dolmuş mu diye kontrol et
            if not self._is_in_cooldown(camera_id, AlarmType.HUMAN_DETECTED):
                
                # Anlık görüntüyü (Snapshot) diske kaydet
                snapshot_path = self._save_snapshot(frame, camera_id, best_detection.bounding_box)
                
                # Alarm nesnesini (entity) oluştur
                alarm = Alarm(
                    id=None,
                    camera_id=camera_id,
                    alarm_type=AlarmType.HUMAN_DETECTED,
                    status=AlarmStatus.NEW,
                    confidence=best_detection.confidence,
                    bounding_box=best_detection.bounding_box,
                    snapshot_path=snapshot_path,
                    message=f"İnsan tespit edildi! Güven (Confidence): %{int(best_detection.confidence * 100)}",
                    created_at=datetime.utcnow()
                )
                
                # Alarmı veritabanına (Repository üzerinden) kaydet
                saved_alarm = self.alarm_repository.add(alarm)
                
                # Bekleme süresini sayacı sıfırla (Update cooldown timestamp)
                self._last_alarms[(camera_id, AlarmType.HUMAN_DETECTED)] = datetime.utcnow()
                
                return saved_alarm

        return None

    def execute(self, camera_id: int) -> Optional[Alarm]:
        """Geriye dönük uyumluluk için: kare okur ve (AI açıksa) tespit çalıştırır."""
        camera = self.camera_repository.get_by_id(camera_id)
        if not camera or not camera.is_enabled_for_detection:
            return None
        frame = self.read_frame(camera_id)
        if frame is None:
            return None
        return self.detect_and_alarm(camera_id, frame)
