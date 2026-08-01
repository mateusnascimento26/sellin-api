from typing import Protocol, Sequence

from domain.entities.typology import Typology


class TypologyRepository(Protocol):
    def list_all(self) -> Sequence[Typology]: ...