from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class NVR:
    id: Optional[int]
    name: str
    host: str
    onvif_port: int = 80
    username: Optional[str] = None
    encrypted_password: Optional[str] = None
    brand: Optional[str] = None
    model: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
