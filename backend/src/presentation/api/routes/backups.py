"""Admin-only system backup endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from fastapi.responses import FileResponse

from src.infrastructure.backup.system_backup import create_backup
from src.infrastructure.security.audit_logger import write_audit_event
from src.presentation.api.dependencies import get_backup_manage_user

router = APIRouter(prefix="/backup", tags=["Backup"])


@router.post("/system")
def download_system_backup(
    request: Request,
    current_user: dict = Depends(get_backup_manage_user),
):
    """Create and download a sensitive system backup archive."""
    source_ip = request.client.host if request.client else None
    actor = current_user.get("sub")
    try:
        backup_path = create_backup()
    except Exception:
        write_audit_event(
            "backup.system.create",
            actor=actor,
            success=False,
            source_ip=source_ip,
        )
        raise

    write_audit_event(
        "backup.system.create",
        actor=actor,
        success=True,
        source_ip=source_ip,
        metadata={
            "filename": backup_path.name,
            "size": backup_path.stat().st_size,
        },
    )
    return FileResponse(
        path=backup_path,
        media_type="application/zip",
        filename=backup_path.name,
    )
