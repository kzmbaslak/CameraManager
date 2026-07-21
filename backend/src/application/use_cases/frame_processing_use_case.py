"""Kamera kare okuma, AI analizi ve alarm uretme use case'leri."""

import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import cv2

from src.domain.entities.alarm import Alarm, AlarmStatus, AlarmType, BoundingBox
from src.domain.entities.camera import CameraStatus
from src.domain.interfaces.ai_inference_service import Detection, IAIInferenceService
from src.domain.interfaces.alarm_repository import IAlarmRepository
from src.domain.interfaces.camera_repository import ICameraRepository
from src.domain.interfaces.frame_source import IFrameSource


@dataclass(frozen=True)
class DetectionAnalysisResult:
    """AI tespit sonucunu, alarmi ve kaynak kare boyutunu birlikte tasir."""

    alarm: Optional[Alarm]
    detections: Tuple[Detection, ...]
    frame_width: Optional[int]
    frame_height: Optional[int]
    detected_at: datetime


class ProcessFrameUseCase:
    """Goruntu okuma, yapay zeka analizi ve alarm uretme is akisini yonetir."""

    def __init__(
        self,
        camera_repository: ICameraRepository,
        alarm_repository: IAlarmRepository,
        frame_source: IFrameSource,
        ai_service: IAIInferenceService,
        snapshot_dir: str = "snapshots",
        cooldown_seconds: int = 60,
    ):
        self.camera_repository = camera_repository
        self.alarm_repository = alarm_repository
        self.frame_source = frame_source
        self.ai_service = ai_service
        self.snapshot_dir = snapshot_dir
        self.cooldown_seconds = cooldown_seconds

        self._last_alarms: Dict[Tuple[int, AlarmType], datetime] = {}
        os.makedirs(self.snapshot_dir, exist_ok=True)

    def _is_in_cooldown(self, camera_id: int, alarm_type: AlarmType) -> bool:
        """Belirtilen kamera ve alarm turu icin cooldown suresini kontrol eder."""
        key = (camera_id, alarm_type)
        if key in self._last_alarms:
            time_since_last = datetime.utcnow() - self._last_alarms[key]
            if time_since_last < timedelta(seconds=self.cooldown_seconds):
                return True
        return False

    def _save_snapshot(self, frame: object, camera_id: int, bounding_box: Optional[BoundingBox] = None) -> str:
        """Goruntuyu diske kaydeder ve dosya yolunu dondurur."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"cam_{camera_id}_{timestamp}.jpg"
        filepath = os.path.join(self.snapshot_dir, filename)

        save_frame = frame.copy()
        if bounding_box:
            x1, y1 = bounding_box.x, bounding_box.y
            x2, y2 = x1 + bounding_box.width, y1 + bounding_box.height
            cv2.rectangle(save_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)

        cv2.imwrite(filepath, save_frame)
        return filepath

    def read_frame(self, camera_id: int, camera=None) -> Optional[object]:
        """Kameradan tek kare okur ve kamera durumunu active/error olarak gunceller."""
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
            if self.alarm_repository is not None:
                for alarm in self.alarm_repository.list_by_camera(camera.id):
                    if alarm.alarm_type == AlarmType.CAMERA_OFFLINE and alarm.status != AlarmStatus.RESOLVED:
                        alarm.resolve(datetime.utcnow())
                        self.alarm_repository.update(alarm)

        return frame

    def analyze_and_alarm(self, camera_id: int, frame: object) -> DetectionAnalysisResult:
        """Verilen karede insanlari tespit eder, gerekirse alarm olusturur."""
        detections = tuple(self.ai_service.detect_humans(frame))
        frame_height = None
        frame_width = None
        if hasattr(frame, "shape") and len(frame.shape) >= 2:
            frame_height = int(frame.shape[0])
            frame_width = int(frame.shape[1])

        saved_alarm = None
        detected_at = datetime.utcnow()

        if detections:
            best_detection = max(detections, key=lambda item: item.confidence)
            if not self._is_in_cooldown(camera_id, AlarmType.HUMAN_DETECTED):
                snapshot_path = self._save_snapshot(frame, camera_id, best_detection.bounding_box)
                alarm = Alarm(
                    id=None,
                    camera_id=camera_id,
                    alarm_type=AlarmType.HUMAN_DETECTED,
                    status=AlarmStatus.NEW,
                    confidence=best_detection.confidence,
                    bounding_box=best_detection.bounding_box,
                    snapshot_path=snapshot_path,
                    message=f"Insan tespit edildi! Guven (Confidence): %{int(best_detection.confidence * 100)}",
                    created_at=detected_at,
                )
                saved_alarm = self.alarm_repository.add(alarm)
                self._last_alarms[(camera_id, AlarmType.HUMAN_DETECTED)] = detected_at

        return DetectionAnalysisResult(
            alarm=saved_alarm,
            detections=detections,
            frame_width=frame_width,
            frame_height=frame_height,
            detected_at=detected_at,
        )

    def detect_and_alarm(self, camera_id: int, frame: object) -> Optional[Alarm]:
        """Geriye donuk uyumluluk icin yalnizca alarm sonucunu dondurur."""
        return self.analyze_and_alarm(camera_id, frame).alarm

    def execute(self, camera_id: int) -> Optional[Alarm]:
        """Kare okur ve AI aciksa insan tespiti/alarm akisini calistirir."""
        camera = self.camera_repository.get_by_id(camera_id)
        if not camera or not camera.is_enabled_for_detection:
            return None
        frame = self.read_frame(camera_id)
        if frame is None:
            return None
        return self.detect_and_alarm(camera_id, frame)
