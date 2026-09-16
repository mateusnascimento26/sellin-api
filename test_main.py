from decimal import Decimal

from domain.value_objects.cnpj import is_valid_cnpj, format_cnpj
from domain.value_objects.dimension import find_dimension
from domain.value_objects.parsing import parse_date, parse_decimal


def test_valid_cnpj():
    assert is_valid_cnpj("07.121.581/0001-69") is True


def test_invalid_cnpj_wrong_check_digit():
    assert is_valid_cnpj("07.121.581/0001-60") is False


def test_invalid_cnpj_all_same_digits():
    assert is_valid_cnpj("11.111.111/1111-11") is False


def test_format_cnpj():
    assert format_cnpj("07121581000169") == "07.121.581/0001-69"


def test_find_dimension_with_comma():
    assert find_dimension("PARATI HD 46x46 A cx 2.3m2") == "46x46"


def test_find_dimension_written_in_meters():
    assert find_dimension("OLIMPO POLIDO HD 60x1,20 A cx 2,88m2") == "60x120"


def test_find_dimension_not_found():
    assert find_dimension("PRODUTO SEM MEDIDA") is None


def test_parse_date_from_text():
    result = parse_date("2022-01-03")
    assert result is not None
    assert result.isoformat() == "2022-01-03"


def test_parse_date_invalid():
    assert parse_date("data invalida") is None


def test_parse_decimal_with_comma():
    assert parse_decimal("165,6") == Decimal("165.6")


def test_parse_decimal_invalid_text():
    assert parse_decimal("ABC") is None