from typing import Sequence
from sqlalchemy.orm import Session
from src.domain.entities.camera import Camera
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
