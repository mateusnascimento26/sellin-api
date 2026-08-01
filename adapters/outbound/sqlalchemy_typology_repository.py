from typing import Sequence

from sqlalchemy.orm import Session

from database import TypologyModel
from domain.entities.typology import Typology


class SqlAlchemyTypologyRepository:
    def __init__(self, session: Session):
        self.session = session

    def list_all(self) -> Sequence[Typology]:
        models = self.session.query(TypologyModel).all()
        return [
            Typology(id=m.id, category=m.category, dimension=m.dimension, created=m.created, end=m.end)
            for m in models
        ]