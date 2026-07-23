"""Kamera kare okuma, AI analizi ve alarm uretme use case'leri."""

import os
import json
import hashlib
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

import cv2

from src.domain.entities.alarm import Alarm, AlarmSeverity, AlarmStatus, AlarmType, BoundingBox
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

    def _file_sha256(self, filepath: str) -> str:
        """Dosyanin SHA-256 ozetini dondurur."""
        with open(filepath, "rb") as file:
            return hashlib.sha256(file.read()).hexdigest()

    def _draw_detection_boxes(self, frame: object, detections: Tuple[Detection, ...]) -> object:
        """Operator kaniti icin tum insan kutularini confidence etiketiyle cizer."""
        annotated = frame.copy()
        for detection in detections:
            box = detection.bounding_box
            x1, y1 = box.x, box.y
            x2, y2 = x1 + box.width, y1 + box.height
            label = f"Insan {int(detection.confidence * 100)}%"
            cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 80, 255), 2)
            label_y = max(16, y1 - 6)
            cv2.rectangle(annotated, (x1, label_y - 15), (x1 + 98, label_y + 4), (0, 80, 255), -1)
            cv2.putText(
                annotated,
                label,
                (x1 + 4, label_y),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.45,
                (20, 20, 20),
                1,
                cv2.LINE_AA,
            )
        return annotated

    def _save_alarm_snapshots(self, frame: object, camera_id: int, detections: Tuple[Detection, ...]) -> tuple[str, str, str, str]:
        """Ham ve kutulu kanit goruntulerini diske kaydeder; yollar ve SHA-256 ozetlerini dondurur."""
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        raw_path = os.path.join(self.snapshot_dir, f"cam_{camera_id}_{timestamp}_raw.jpg")
        annotated_path = os.path.join(self.snapshot_dir, f"cam_{camera_id}_{timestamp}_boxed.jpg")

        cv2.imwrite(raw_path, frame)
        cv2.imwrite(annotated_path, self._draw_detection_boxes(frame, detections))
        return raw_path, self._file_sha256(raw_path), annotated_path, self._file_sha256(annotated_path)

    def _is_ai_schedule_active(self, camera) -> bool:
        """Kamera bazli AI aktif saat araligini kontrol eder."""
        if not camera or not camera.ai_active_start or not camera.ai_active_end:
            return True
        now_value = datetime.now().strftime("%H:%M")
        start = camera.ai_active_start
        end = camera.ai_active_end
        if start <= end:
            return start <= now_value <= end
        return now_value >= start or now_value <= end

    def _is_point_in_polygon(self, x: float, y: float, polygon: list[dict]) -> bool:
        """Ray casting ile normalize noktanin ROI poligonu icinde olup olmadigini dondurur."""
        inside = False
        j = len(polygon) - 1
        for i, point in enumerate(polygon):
            xi = float(point["x"])
            yi = float(point["y"])
            xj = float(polygon[j]["x"])
            yj = float(polygon[j]["y"])
            intersects = ((yi > y) != (yj > y)) and (
                x < (xj - xi) * (y - yi) / ((yj - yi) or 1e-9) + xi
            )
            if intersects:
                inside = not inside
            j = i
        return inside

    def _filter_roi(self, detections: Tuple[Detection, ...], camera, frame_width: Optional[int], frame_height: Optional[int]) -> Tuple[Detection, ...]:
        """ROI poligonu tanimliysa kutu merkezleri poligon disinda kalan tespitleri eler."""
        if not camera or not camera.ai_roi_polygon or not frame_width or not frame_height:
            return detections
        try:
            polygon = json.loads(camera.ai_roi_polygon)
        except (TypeError, ValueError):
            return detections
        if not isinstance(polygon, list) or len(polygon) < 3:
            return detections

        filtered = []
        for detection in detections:
            box = detection.bounding_box
            cx = (box.x + box.width / 2) / frame_width
            cy = (box.y + box.height / 2) / frame_height
            if self._is_point_in_polygon(cx, cy, polygon):
                filtered.append(detection)
        return tuple(filtered)

    def _resize_frame_for_ai(self, frame: object, camera) -> tuple[object, float]:
        """AI icin kareyi kucultur; bounding box geri olcegi icin oran dondurur."""
        target_width = getattr(camera, "ai_inference_width", 640) or 640
        if not hasattr(frame, "shape") or len(frame.shape) < 2:
            return frame, 1.0
        original_width = int(frame.shape[1])
        original_height = int(frame.shape[0])
        if original_width <= 0 or original_width <= target_width:
            return frame, 1.0
        scale = target_width / original_width
        target_height = max(1, int(round(original_height * scale)))
        return cv2.resize(frame, (target_width, target_height), interpolation=cv2.INTER_AREA), scale

    def _scale_detections(self, detections: Tuple[Detection, ...], scale: float, frame_width: Optional[int], frame_height: Optional[int]) -> Tuple[Detection, ...]:
        """Kucuk AI karesindeki kutulari orijinal kare koordinatina tasir."""
        if scale == 1.0:
            return detections
        scaled: list[Detection] = []
        for detection in detections:
            box = detection.bounding_box
            x = int(round(box.x / scale))
            y = int(round(box.y / scale))
            width = int(round(box.width / scale))
            height = int(round(box.height / scale))
            if frame_width is not None:
                x = max(0, min(x, frame_width - 1))
                width = max(1, min(width, frame_width - x))
            if frame_height is not None:
                y = max(0, min(y, frame_height - 1))
                height = max(1, min(height, frame_height - y))
            scaled.append(Detection(
                label=detection.label,
                confidence=detection.confidence,
                bounding_box=BoundingBox(x=x, y=y, width=width, height=height),
            ))
        return tuple(scaled)

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

    def analyze_and_alarm(self, camera_id: int, frame: object, camera=None) -> DetectionAnalysisResult:
        """Verilen karede insanlari tespit eder, gerekirse alarm olusturur."""
        frame_height = None
        frame_width = None
        if hasattr(frame, "shape") and len(frame.shape) >= 2:
            frame_height = int(frame.shape[0])
            frame_width = int(frame.shape[1])

        saved_alarm = None
        detected_at = datetime.utcnow()
        if not self._is_ai_schedule_active(camera):
            return DetectionAnalysisResult(
                alarm=None,
                detections=(),
                frame_width=frame_width,
                frame_height=frame_height,
                detected_at=detected_at,
            )

        ai_frame, ai_scale = self._resize_frame_for_ai(frame, camera)
        detections = tuple(self.ai_service.detect_humans(
            ai_frame,
            conf_threshold=getattr(camera, "ai_confidence_threshold", None),
            iou_threshold=getattr(camera, "ai_iou_threshold", None),
        ))
        detections = self._scale_detections(detections, ai_scale, frame_width, frame_height)
        detections = self._filter_roi(detections, camera, frame_width, frame_height)

        if detections:
            best_detection = max(detections, key=lambda item: item.confidence)
            cooldown_seconds = getattr(camera, "ai_alarm_cooldown_seconds", None)
            original_cooldown = self.cooldown_seconds
            if cooldown_seconds:
                self.cooldown_seconds = cooldown_seconds
            in_cooldown = self._is_in_cooldown(camera_id, AlarmType.HUMAN_DETECTED)
            self.cooldown_seconds = original_cooldown
            if not in_cooldown:
                snapshot_path, snapshot_sha256, snapshot_annotated_path, snapshot_annotated_sha256 = self._save_alarm_snapshots(frame, camera_id, detections)
                alarm = Alarm(
                    id=None,
                    camera_id=camera_id,
                    alarm_type=AlarmType.HUMAN_DETECTED,
                    status=AlarmStatus.NEW,
                    confidence=best_detection.confidence,
                    bounding_box=best_detection.bounding_box,
                    snapshot_path=snapshot_path,
                    snapshot_sha256=snapshot_sha256,
                    snapshot_annotated_path=snapshot_annotated_path,
                    snapshot_annotated_sha256=snapshot_annotated_sha256,
                    severity=AlarmSeverity.HIGH,
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
