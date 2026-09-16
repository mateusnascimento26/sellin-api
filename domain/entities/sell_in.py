from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal


@dataclass
class SellIn:
    invoice_number: str
    customer_name: str
    customer_cnpj: str
    representative_name: str
    product_code: str
    product_name: str
    sale_date: date
    quantity: Decimal
    amount: Decimal
    typology_id: int
    id: int | None = None
    created: datetime | None = None
    end: datetime | None = None