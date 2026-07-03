from fastapi import APIRouter
from src.presentation.api.routes.cameras import router as cameras_router
from src.presentation.api.routes.alarms import router as alarms_router
from src.presentation.api.routes.users import router as users_router
from src.presentation.api.routes.streams import router as streams_router
from src.presentation.api.routes.nvrs import router as nvrs_router
from src.presentation.api.routes.auth import router as auth_router

router = APIRouter()

@router.get("/health")
def health_check():
    """Sistemin ayakta olup olmadığını kontrol eder (Health Check)."""
    return {"status": "healthy"}

router.include_router(cameras_router)
router.include_router(alarms_router)
router.include_router(users_router)
router.include_router(streams_router)
router.include_router(nvrs_router)
router.include_router(auth_router)
