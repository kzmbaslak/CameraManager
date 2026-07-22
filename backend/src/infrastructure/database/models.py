from datetime import datetime
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Float, ForeignKey, Enum
from sqlalchemy.orm import relationship

from .database import Base
from src.domain.entities.camera import CameraStatus
from src.domain.entities.user import UserRole
from src.domain.entities.alarm import AlarmStatus, AlarmType


class NVRModel(Base):
    __tablename__ = "nvrs"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    host = Column(String)
    onvif_port = Column(Integer, default=80)
    username = Column(String, nullable=True)
    encrypted_password = Column(String, nullable=True)
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    cameras = relationship("CameraModel", back_populates="nvr")


class CameraModel(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    host = Column(String)
    rtsp_port = Column(Integer, default=554)
    onvif_port = Column(Integer, default=80)
    username = Column(String, nullable=True)
    encrypted_password = Column(String, nullable=True)
    rtsp_path = Column(String, default="")
    status = Column(Enum(CameraStatus), default=CameraStatus.INACTIVE)
    motion_detection_enabled = Column(Boolean, default=False)
    ai_detection_enabled = Column(Boolean, default=False)
    ai_confidence_threshold = Column(Float, default=0.5)
    ai_iou_threshold = Column(Float, default=0.45)
    ai_alarm_cooldown_seconds = Column(Integer, default=60)
    ai_active_start = Column(String, nullable=True)
    ai_active_end = Column(String, nullable=True)
    ai_roi_polygon = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    brand = Column(String, nullable=True)
    model = Column(String, nullable=True)
    nvr_id = Column(Integer, ForeignKey("nvrs.id", ondelete="SET NULL"), nullable=True)

    alarms = relationship("AlarmModel", back_populates="camera", cascade="all, delete-orphan")
    nvr = relationship("NVRModel", back_populates="cameras")


class UserModel(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password_hash = Column(String)
    role = Column(Enum(UserRole), default=UserRole.VIEWER)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AlarmModel(Base):
    __tablename__ = "alarms"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id"))
    alarm_type = Column(Enum(AlarmType))
    status = Column(Enum(AlarmStatus), default=AlarmStatus.NEW)
    confidence = Column(Float, nullable=True)

    bbox_x = Column(Integer, nullable=True)
    bbox_y = Column(Integer, nullable=True)
    bbox_width = Column(Integer, nullable=True)
    bbox_height = Column(Integer, nullable=True)

    snapshot_path = Column(String, nullable=True)
    message = Column(String, nullable=True)
    severity = Column(String, default="medium")
    false_positive = Column(Boolean, default=False)
    assigned_to = Column(String, nullable=True)
    operator_note = Column(String, nullable=True)
    resolution_reason = Column(String, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    camera = relationship("CameraModel", back_populates="alarms")


class CameraHealthSampleModel(Base):
    __tablename__ = "camera_health_samples"

    id = Column(Integer, primary_key=True, index=True)
    camera_id = Column(Integer, ForeignKey("cameras.id", ondelete="CASCADE"), index=True)
    checked_at = Column(DateTime, default=datetime.utcnow, index=True)
    reachable = Column(Boolean, default=False)
    status = Column(String, default="unknown")
    latency_ms = Column(Float, nullable=True)
    failure_reason = Column(String, nullable=True)
