from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from src.domain.entities.alarm import AlarmSeverity, AlarmStatus, AlarmType

class BoundingBoxSchema(BaseModel):
    x: int
    y: int
    width: int
    height: int

class AlarmResponse(BaseModel):
    id: int
    camera_id: int
    alarm_type: AlarmType
    status: AlarmStatus
    confidence: Optional[float]
    bounding_box: Optional[BoundingBoxSchema]
    snapshot_path: Optional[str]
    snapshot_sha256: Optional[str] = None
    snapshot_annotated_path: Optional[str] = None
    snapshot_annotated_sha256: Optional[str] = None
    message: Optional[str]
    severity: AlarmSeverity = AlarmSeverity.MEDIUM
    false_positive: bool = False
    assigned_to: Optional[str] = None
    operator_note: Optional[str] = None
    resolution_reason: Optional[str] = None
    created_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True


class AlarmTrainingFeedbackItem(BaseModel):
    """AI iyilestirme havuzuna aktarilacak sinirli alarm ozeti."""

    alarm_id: int
    camera_id: int
    created_at: Optional[datetime]
    confidence: Optional[float]
    bounding_box: Optional[BoundingBoxSchema]
    false_positive: bool
    severity: AlarmSeverity
    operator_note: Optional[str] = None
    resolution_reason: Optional[str] = None
    snapshot_sha256: Optional[str] = None
    snapshot_annotated_sha256: Optional[str] = None


class AlarmEvidenceFileItem(BaseModel):
    """Kanit manifestindeki tek dosya ozeti; dosya yolu dondurmez."""

    variant: str
    available: bool
    filename: Optional[str] = None
    sha256: Optional[str] = None
    size_bytes: Optional[int] = None
    status: str


class AlarmEvidenceManifest(BaseModel):
    """Alarm kanit zinciri icin indirilebilir, yol sizdirmayan manifest."""

    alarm_id: int
    camera_id: int
    alarm_type: AlarmType
    status: AlarmStatus
    severity: AlarmSeverity
    false_positive: bool
    confidence: Optional[float] = None
    bounding_box: Optional[BoundingBoxSchema] = None
    created_at: Optional[datetime] = None
    acknowledged_at: Optional[datetime] = None
    resolved_at: Optional[datetime] = None
    generated_at: datetime
    files: List[AlarmEvidenceFileItem]


class AlarmThresholdSuggestionItem(BaseModel):
    """Kamera bazli yanlis alarm ve confidence esigi onerisi."""

    camera_id: int
    sample_count: int
    false_positive_count: int
    false_positive_rate: float
    average_confidence: Optional[float] = None
    suggested_confidence_threshold: Optional[float] = None
    recommendation: str


class AlarmThresholdSuggestionApplyRequest(BaseModel):
    """Onerilen confidence esiklerini secili kameralara uygular."""

    camera_ids: Optional[List[int]] = None
    limit: int = Field(default=1000, ge=1, le=5000)
    minimum_samples: int = Field(default=3, ge=1, le=50)


class AlarmThresholdSuggestionApplyItem(BaseModel):
    """Tek kamera icin uygulanan threshold degisikligi."""

    camera_id: int
    previous_confidence_threshold: float
    applied_confidence_threshold: float
    sample_count: int
    false_positive_rate: float


class AlarmThresholdSuggestionApplyResponse(BaseModel):
    """Toplu threshold uygulama sonucu."""

    applied_count: int
    skipped_count: int
    items: List[AlarmThresholdSuggestionApplyItem]


class AlarmUpdate(BaseModel):
    """Alarm operasyon alanlarini kismi olarak gunceller."""

    assigned_to: Optional[str] = Field(default=None, max_length=128)
    operator_note: Optional[str] = Field(default=None, max_length=2000)
    severity: Optional[AlarmSeverity] = None
    false_positive: Optional[bool] = None


class AlarmResolveRequest(BaseModel):
    """Alarm kapatma istegi."""

    resolution_reason: Optional[str] = Field(default=None, max_length=500)
    false_positive: bool = False
