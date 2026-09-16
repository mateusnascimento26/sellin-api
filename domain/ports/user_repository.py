from typing import Protocol

from domain.entities.user import User


class UserRepository(Protocol):
    def get_by_username(self, username: str) -> User | None: ...