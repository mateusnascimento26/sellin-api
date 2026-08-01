from datetime import datetime

from dotenv import load_dotenv
import os

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    create_engine,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+psycopg://sellin:sellin@localhost:5432/sellin")

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, future=True)


class Base(DeclarativeBase):
    pass


class TypologyModel(Base):
    __tablename__ = "typology"
    __table_args__ = (UniqueConstraint("category", "dimension", name="uq_typology_category_dimension"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    category: Mapped[str] = mapped_column(String(50), nullable=False)
    dimension: Mapped[str] = mapped_column(String(30), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class SellInModel(Base):
    __tablename__ = "sell_in"
    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_sell_in_quantity_positive"),
        CheckConstraint("amount >= 0", name="ck_sell_in_amount_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    invoice_number: Mapped[str] = mapped_column(String(30), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    customer_cnpj: Mapped[str] = mapped_column(String(18), nullable=False)
    representative_name: Mapped[str] = mapped_column(String(255), nullable=False)
    product_code: Mapped[str] = mapped_column(String(50), nullable=False)
    product_name: Mapped[str] = mapped_column(String(500), nullable=False)
    sale_date: Mapped[datetime] = mapped_column(Date, nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    amount: Mapped[float] = mapped_column(Numeric(18, 4), nullable=False)
    typology_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("typology.id"), nullable=False)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


INITIAL_TYPOLOGIES = [
    ("Cerâmica", "33x46"),
    ("Cerâmica", "46x46"),
    ("Cerâmica", "57x57"),
    ("Porcelanato", "30x61"),
    ("Porcelanato", "34x70"),
    ("Porcelanato", "60x120"),
    ("Porcelanato", "120x120"),
    ("Porcelanato", "70x70"),
    ("Porcelanato", "94.5x94.5"),
    ("Super Prime", "32x65"),
    ("Super Prime", "17x106"),
    ("Super Prime", "56x56"),
    ("Super Prime", "75x75"),
    ("Super Prime", "100x100"),
]


def create_tables_and_seed():
    Base.metadata.create_all(engine)
    with SessionLocal() as session:
        existing = session.query(TypologyModel).count()
        if existing == 0:
            for category, dimension in INITIAL_TYPOLOGIES:
                session.add(TypologyModel(category=category, dimension=dimension))
            session.commit()
            print("Tipologias iniciais inseridas.")
        else:
            print("Tipologias já existiam, nada foi inserido.")


if __name__ == "__main__":
    create_tables_and_seed()