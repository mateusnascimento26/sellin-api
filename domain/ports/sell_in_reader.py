from typing import Protocol

from domain.entities.sale_record import SaleRecord


class SellInReader(Protocol):
    def read(self, file_content: bytes) -> list[SaleRecord]:
        ...