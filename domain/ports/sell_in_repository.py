from typing import Protocol, Sequence

from domain.entities.sell_in import SellIn


class SellInRepository(Protocol):
    def delete_all(self) -> None: ...

    def save_all(self, records: Sequence[SellIn]) -> None: ...