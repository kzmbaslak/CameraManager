from __future__ import annotations

from typing import Protocol, Sequence

from src.domain.entities.user import User


class IUserRepository(Protocol):
    def add(self, user: User) -> User:
        ...

    def get_by_id(self, user_id: int) -> User | None:
        ...

    def get_by_username(self, username: str) -> User | None:
        ...

    def list_all(self) -> Sequence[User]:
        ...

    def update(self, user: User) -> User:
        ...
