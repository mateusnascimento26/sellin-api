from typing import Sequence

from sqlalchemy.orm import Session

from database import SellInModel
from domain.entities.sell_in import SellIn


class SqlAlchemySellInRepository:
    def __init__(self, session: Session):
        self.session = session

    def delete_all(self) -> None:
        self.session.query(SellInModel).delete()

    def save_all(self, records: Sequence[SellIn]) -> None:
        models = [
            SellInModel(
                invoice_number=r.invoice_number,
                customer_name=r.customer_name,
                customer_cnpj=r.customer_cnpj,
                representative_name=r.representative_name,
                product_code=r.product_code,
                product_name=r.product_name,
                sale_date=r.sale_date,
                quantity=r.quantity,
                amount=r.amount,
                typology_id=r.typology_id,
            )
            for r in records
        ]
        self.session.add_all(models)