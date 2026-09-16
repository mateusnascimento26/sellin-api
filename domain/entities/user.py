from dataclasses import dataclass
from datetime import datetime


@dataclass
class User:
    username: str
    password_hash: str
    id: int | None = None
    created: datetime | None = None