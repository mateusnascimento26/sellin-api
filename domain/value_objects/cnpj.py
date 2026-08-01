import re

_ONLY_DIGITS = re.compile(r"\D")


def only_digits(text: str) -> str:
    return _ONLY_DIGITS.sub("", text or "")


def is_valid_cnpj(raw: str) -> bool:
    digits = only_digits(raw)
    if len(digits) != 14:
        return False
    if digits == digits[0] * 14:
        return False

    def calc_digit(base: str, weights: list[int]) -> int:
        total = sum(int(d) * w for d, w in zip(base, weights))
        remainder = total % 11
        return 0 if remainder < 2 else 11 - remainder

    dv1 = calc_digit(digits[:12], [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if dv1 != int(digits[12]):
        return False

    dv2 = calc_digit(digits[:13], [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2])
    if dv2 != int(digits[13]):
        return False

    return True


def format_cnpj(raw: str) -> str:
    digits = only_digits(raw)
    return f"{digits[0:2]}.{digits[2:5]}.{digits[5:8]}/{digits[8:12]}-{digits[12:14]}"