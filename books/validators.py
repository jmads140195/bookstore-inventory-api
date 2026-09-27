import re

import pycountry
from django.core.exceptions import ValidationError


def normalize_isbn(value):
    return re.sub(r"[\s-]", "", value).upper()


def validate_isbn(value):
    if re.fullmatch(r"[0-9]{9}[0-9X]", value):
        digits = [10 if ch == "X" else int(ch) for ch in value]
        valid = sum((10 - i) * digit for i, digit in enumerate(digits)) % 11 == 0
    elif re.fullmatch(r"97[89][0-9]{10}", value):
        valid = sum(int(ch) * (1 if i % 2 == 0 else 3) for i, ch in enumerate(value)) % 10 == 0
    else:
        valid = False
    if not valid:
        raise ValidationError("ISBN inválido: revisa el formato y el dígito de control.", code="invalid_isbn")


def validate_country(value):
    if not pycountry.countries.get(alpha_2=value):
        raise ValidationError("Usa un código de país ISO 3166-1 válido, como ES.", code="invalid_country")
