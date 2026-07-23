from typing import Sequence
from sqlalchemy import or_
from sqlalchemy.orm import Session
from src.domain.entities.camera import Camera, CameraStatus
from src.domain.interfaces.camera_repository import ICameraRepository
from src.infrastructure.database.models import CameraModel


class SqlAlchemyCameraRepository(ICameraRepository):
    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: CameraModel) -> Camera:
        return Camera(
            id=model.id,
            name=model.name,
            host=model.host,
            rtsp_port=model.rtsp_port,
            onvif_port=model.onvif_port,
            username=model.username,
            encrypted_password=model.encrypted_password,
            rtsp_path=model.rtsp_path,
            status=model.status,
            motion_detection_enabled=model.motion_detection_enabled,
            ai_detection_enabled=model.ai_detection_enabled,
            ai_confidence_threshold=model.ai_confidence_threshold if model.ai_confidence_threshold is not None else 0.5,
            ai_iou_threshold=model.ai_iou_threshold if model.ai_iou_threshold is not None else 0.45,
            ai_alarm_cooldown_seconds=model.ai_alarm_cooldown_seconds or 60,
            ai_frame_stride=model.ai_frame_stride or 1,
            ai_inference_width=model.ai_inference_width or 640,
            ai_active_start=model.ai_active_start,
            ai_active_end=model.ai_active_end,
            ai_roi_polygon=model.ai_roi_polygon,
            created_at=model.created_at,
            updated_at=model.updated_at,
            brand=model.brand,
            model=model.model,
            nvr_id=model.nvr_id,
        )

    def _to_model(self, entity: Camera) -> CameraModel:
        return CameraModel(
            id=entity.id,
            name=entity.name,
            host=entity.host,
            rtsp_port=entity.rtsp_port,
            onvif_port=entity.onvif_port,
            username=entity.username,
            encrypted_password=entity.encrypted_password,
            rtsp_path=entity.rtsp_path,
            status=entity.status,
            motion_detection_enabled=entity.motion_detection_enabled,
            ai_detection_enabled=entity.ai_detection_enabled,
            ai_confidence_threshold=entity.ai_confidence_threshold,
            ai_iou_threshold=entity.ai_iou_threshold,
            ai_alarm_cooldown_seconds=entity.ai_alarm_cooldown_seconds,
            ai_frame_stride=entity.ai_frame_stride,
            ai_inference_width=entity.ai_inference_width,
            ai_active_start=entity.ai_active_start,
            ai_active_end=entity.ai_active_end,
            ai_roi_polygon=entity.ai_roi_polygon,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            brand=entity.brand,
            model=entity.model,
            nvr_id=entity.nvr_id,
        )

    def add(self, camera: Camera) -> Camera:
        model = self._to_model(camera)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, camera_id: int) -> Camera | None:
        model = self._db.query(CameraModel).filter(CameraModel.id == camera_id).first()
        return self._to_entity(model) if model else None

    def list_all(self) -> Sequence[Camera]:
        return [
            self._to_entity(m)
            for m in self._db.query(CameraModel).order_by(CameraModel.id).all()
        ]

    def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "all",
        ai_filter: str = "all",
        sort: str = "name_asc",
    ) -> tuple[Sequence[Camera], int]:
        query = self._db.query(CameraModel)
        needle = search.strip()
        if needle:
            like = f"%{needle}%"
            query = query.filter(or_(
                CameraModel.name.ilike(like),
                CameraModel.host.ilike(like),
                CameraModel.rtsp_path.ilike(like),
                CameraModel.brand.ilike(like),
                CameraModel.model.ilike(like),
            ))
        if status != "all":
            query = query.filter(CameraModel.status == CameraStatus(status))
        if ai_filter == "enabled":
            query = query.filter(CameraModel.ai_detection_enabled.is_(True))
        elif ai_filter == "disabled":
            query = query.filter(CameraModel.ai_detection_enabled.is_(False))

        total = query.count()
        if sort == "name_desc":
            query = query.order_by(CameraModel.name.desc())
        elif sort == "status":
            query = query.order_by(CameraModel.status.asc(), CameraModel.name.asc())
        elif sort == "id_desc":
            query = query.order_by(CameraModel.id.desc())
        else:
            query = query.order_by(CameraModel.name.asc())

        offset = max(page - 1, 0) * page_size
        models = query.offset(offset).limit(page_size).all()
        return [self._to_entity(m) for m in models], total

    def list_by_nvr(self, nvr_id: int) -> Sequence[Camera]:
        return [
            self._to_entity(m)
            for m in self._db.query(CameraModel).filter(CameraModel.nvr_id == nvr_id).all()
        ]

    def update(self, camera: Camera) -> Camera:
        model = self._db.query(CameraModel).filter(CameraModel.id == camera.id).first()
        if not model:
            raise ValueError(f"Kamera {camera.id} bulunamadı.")
        model.name = camera.name
        model.host = camera.host
        model.rtsp_port = camera.rtsp_port
        model.onvif_port = camera.onvif_port
        model.username = camera.username
        model.encrypted_password = camera.encrypted_password
        model.rtsp_path = camera.rtsp_path
        model.status = camera.status
        model.motion_detection_enabled = camera.motion_detection_enabled
        model.ai_detection_enabled = camera.ai_detection_enabled
        model.ai_confidence_threshold = camera.ai_confidence_threshold
        model.ai_iou_threshold = camera.ai_iou_threshold
        model.ai_alarm_cooldown_seconds = camera.ai_alarm_cooldown_seconds
        model.ai_frame_stride = camera.ai_frame_stride
        model.ai_inference_width = camera.ai_inference_width
        model.ai_active_start = camera.ai_active_start
        model.ai_active_end = camera.ai_active_end
        model.ai_roi_polygon = camera.ai_roi_polygon
        model.brand = camera.brand
        model.model = camera.model
        model.nvr_id = camera.nvr_id
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def delete(self, camera_id: int) -> None:
        model = self._db.query(CameraModel).filter(CameraModel.id == camera_id).first()
        if model:
            self._db.delete(model)
            self._db.commit()
