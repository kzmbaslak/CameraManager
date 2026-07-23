from typing import Sequence
from sqlalchemy import or_
from sqlalchemy.orm import Session
from src.domain.entities.nvr import NVR
from src.domain.interfaces.nvr_repository import INVRRepository
from src.infrastructure.database.models import NVRModel


class SqlAlchemyNVRRepository(INVRRepository):
    def __init__(self, db: Session):
        self._db = db

    def _to_entity(self, model: NVRModel) -> NVR:
        return NVR(
            id=model.id,
            name=model.name,
            host=model.host,
            onvif_port=model.onvif_port,
            username=model.username,
            encrypted_password=model.encrypted_password,
            brand=model.brand,
            model=model.model,
            is_active=model.is_active,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    def _to_model(self, entity: NVR) -> NVRModel:
        return NVRModel(
            id=entity.id,
            name=entity.name,
            host=entity.host,
            onvif_port=entity.onvif_port,
            username=entity.username,
            encrypted_password=entity.encrypted_password,
            brand=entity.brand,
            model=entity.model,
            is_active=entity.is_active,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
        )

    def add(self, nvr: NVR) -> NVR:
        model = self._to_model(nvr)
        self._db.add(model)
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def get_by_id(self, nvr_id: int) -> NVR | None:
        model = self._db.query(NVRModel).filter(NVRModel.id == nvr_id).first()
        return self._to_entity(model) if model else None

    def list_all(self) -> Sequence[NVR]:
        return [self._to_entity(m) for m in self._db.query(NVRModel).all()]

    def list_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "all",
        sort: str = "name_asc",
    ) -> tuple[Sequence[NVR], int]:
        query = self._db.query(NVRModel)
        needle = search.strip()
        if needle:
            like = f"%{needle}%"
            query = query.filter(or_(
                NVRModel.name.ilike(like),
                NVRModel.host.ilike(like),
                NVRModel.brand.ilike(like),
                NVRModel.model.ilike(like),
                NVRModel.username.ilike(like),
            ))
        if status == "active":
            query = query.filter(NVRModel.is_active.is_(True))
        elif status == "inactive":
            query = query.filter(NVRModel.is_active.is_(False))

        total = query.count()
        if sort == "name_desc":
            query = query.order_by(NVRModel.name.desc())
        elif sort == "host":
            query = query.order_by(NVRModel.host.asc(), NVRModel.name.asc())
        elif sort == "status":
            query = query.order_by(NVRModel.is_active.desc(), NVRModel.name.asc())
        elif sort == "id_desc":
            query = query.order_by(NVRModel.id.desc())
        else:
            query = query.order_by(NVRModel.name.asc())

        offset = max(page - 1, 0) * page_size
        models = query.offset(offset).limit(page_size).all()
        return [self._to_entity(m) for m in models], total

    def update(self, nvr: NVR) -> NVR:
        model = self._db.query(NVRModel).filter(NVRModel.id == nvr.id).first()
        if not model:
            raise ValueError(f"NVR {nvr.id} bulunamadı.")
        model.name = nvr.name
        model.host = nvr.host
        model.onvif_port = nvr.onvif_port
        model.username = nvr.username
        model.encrypted_password = nvr.encrypted_password
        model.brand = nvr.brand
        model.model = nvr.model
        model.is_active = nvr.is_active
        self._db.commit()
        self._db.refresh(model)
        return self._to_entity(model)

    def delete(self, nvr_id: int) -> None:
        model = self._db.query(NVRModel).filter(NVRModel.id == nvr_id).first()
        if model:
            self._db.delete(model)
            self._db.commit()
