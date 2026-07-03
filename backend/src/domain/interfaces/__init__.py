from src.domain.interfaces.ai_inference_service import Detection, IAIInferenceService
from src.domain.interfaces.alarm_repository import IAlarmRepository
from src.domain.interfaces.camera_repository import ICameraRepository
from src.domain.interfaces.frame_source import IFrameSource
from src.domain.interfaces.user_repository import IUserRepository

__all__ = [
    "Detection",
    "IAIInferenceService",
    "IAlarmRepository",
    "ICameraRepository",
    "IFrameSource",
    "IUserRepository",
]
