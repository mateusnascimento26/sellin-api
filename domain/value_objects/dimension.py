import re
from decimal import Decimal

DIMENSION_PATTERN = re.compile(r"(\d+(?:[.,]\d+)?)\s*[xX×]\s*(\d+(?:[.,]\d+)?)")


def normalize_number(raw: str) -> str:
    value = Decimal(raw.replace(",", "."))
    if value < 10:  # escrito em metros (ex.: "1,20"), converte para centímetros
        value = value * 100
    if value == value.to_integral_value():
        return str(int(value))
    return str(value.normalize())


def find_dimension(product_name: str) -> str | None:
    match = DIMENSION_PATTERN.search(product_name or "")
    if not match:
        return None
    return f"{normalize_number(match.group(1))}x{normalize_number(match.group(2))}"