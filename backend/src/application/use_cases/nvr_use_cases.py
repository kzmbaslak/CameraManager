from typing import Optional, Sequence
from src.domain.entities.nvr import NVR
from src.domain.interfaces.nvr_repository import INVRRepository


class NVRUseCases:
    """NVR cihazı yönetimi iş mantığını yöneten kullanım senaryosu sınıfı."""

    def __init__(self, nvr_repository: INVRRepository, password_service=None):
        self._repo = nvr_repository
        self._password_service = password_service

    def _encrypt_password(self, plain: Optional[str]) -> Optional[str]:
        if plain and self._password_service:
            return self._password_service.encrypt(plain)
        return plain

    def add_nvr(
        self,
        name: str,
        host: str,
        onvif_port: int = 80,
        username: Optional[str] = None,
        password: Optional[str] = None,
        brand: Optional[str] = None,
        model: Optional[str] = None,
    ) -> NVR:
        if not name or not host:
            raise ValueError("NVR adı ve sunucu adresi zorunludur.")

        # Aynı IP'ye sahip NVR zaten var mı kontrol et (Upsert mantığı)
        existing_nvrs = self._repo.list_all()
        target_host = host.strip().lower()
        existing = None
        
        for n in existing_nvrs:
            if n.host and n.host.strip().lower() == target_host:
                existing = n
                break

        if existing:
            # Üzerine yaz
            existing.name = name
            existing.onvif_port = onvif_port
            existing.username = username
            if password is not None:
                existing.encrypted_password = self._encrypt_password(password)
            if brand is not None:
                existing.brand = brand
            if model is not None:
                existing.model = model
            return self._repo.update(existing)

        nvr = NVR(
            id=None,
            name=name,
            host=host,
            onvif_port=onvif_port,
            username=username,
            encrypted_password=self._encrypt_password(password),
            brand=brand,
            model=model,
            is_active=True,
        )
        return self._repo.add(nvr)

    def list_nvrs(self) -> Sequence[NVR]:
        return self._repo.list_all()

    def list_nvrs_paginated(
        self,
        *,
        page: int = 1,
        page_size: int = 25,
        search: str = "",
        status: str = "all",
        sort: str = "name_asc",
    ) -> tuple[Sequence[NVR], int]:
        return self._repo.list_paginated(
            page=page,
            page_size=page_size,
            search=search,
            status=status,
            sort=sort,
        )

    def get_nvr(self, nvr_id: int) -> Optional[NVR]:
        return self._repo.get_by_id(nvr_id)

    def delete_nvr(self, nvr_id: int) -> None:
        self._repo.delete(nvr_id)

    def update_nvr(self, nvr: NVR, plain_password: Optional[str] = None) -> NVR:
        if plain_password is not None:
            nvr.encrypted_password = self._encrypt_password(plain_password)
        return self._repo.update(nvr)

    def bulk_add_nvrs(self, nvrs_list: list) -> list[NVR]:
        """Birden fazla NVR cihazını toplu ekler. IP çakışırsa üzerine yazar (Upsert)."""
        existing_nvrs = self._repo.list_all()
        existing_lookup = {
            n.host.strip().lower(): n 
            for n in existing_nvrs 
            if n.host
        }

        added_nvrs = []
        for item in nvrs_list:
            name = item.get("name")
            host = item.get("host")
            onvif_port = item.get("onvif_port", 80)
            username = item.get("username")
            password = item.get("password")
            brand = item.get("brand")
            model = item.get("model")

            if not name or not host:
                continue

            target_host = host.strip().lower()
            if target_host in existing_lookup:
                # Üzerine yaz
                existing = existing_lookup[target_host]
                existing.name = name
                existing.onvif_port = onvif_port
                existing.username = username
                if password is not None:
                    existing.encrypted_password = self._encrypt_password(password)
                if brand is not None:
                    existing.brand = brand
                if model is not None:
                    existing.model = model
                added = self._repo.update(existing)
                added_nvrs.append(added)
            else:
                nvr = NVR(
                    id=None,
                    name=name,
                    host=host,
                    onvif_port=onvif_port,
                    username=username,
                    encrypted_password=self._encrypt_password(password),
                    brand=brand,
                    model=model,
                    is_active=True,
                )
                added = self._repo.add(nvr)
                existing_lookup[target_host] = added
                added_nvrs.append(added)

        return added_nvrs
