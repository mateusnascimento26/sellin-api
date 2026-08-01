from dataclasses import dataclass
from datetime import datetime


@dataclass
class Typology:
    category: str
    dimension: str
    id: int | None = None
    created: datetime | None = None
    end: datetime | None = None