from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from src.domain.entities.alarm import AlarmStatus, AlarmType

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
    message: Optional[str]
    created_at: Optional[datetime]
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]

    class Config:
        from_attributes = True
