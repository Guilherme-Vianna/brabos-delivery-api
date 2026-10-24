from decimal import Decimal
from typing import Annotated

from pydantic import AfterValidator, BeforeValidator, Field, PlainSerializer, StringConstraints

RESERVED_SLUGS = {"me"}


def _check_cnpj(value: str) -> str:
    digits = [int(char) for char in value]
    if len(set(digits)) == 1:
        raise ValueError("Invalid CNPJ")
    for size in (12, 13):
        weights = list(range(size - 7, 1, -1)) + list(range(9, 1, -1))
        remainder = sum(d * w for d, w in zip(digits[:size], weights, strict=True)) % 11
        if digits[size] != (0 if remainder < 2 else 11 - remainder):
            raise ValueError("Invalid CNPJ")
    return value


def _check_slug(value: str) -> str:
    if value in RESERVED_SLUGS:
        raise ValueError("Slug is reserved")
    return value


def _digits(value: str) -> str:
    return "".join(char for char in value if char.isdigit())


EstablishmentName = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=150)
]
FullName = Annotated[str, StringConstraints(strip_whitespace=True, min_length=2, max_length=150)]
Address = Annotated[str, StringConstraints(strip_whitespace=True, min_length=5, max_length=300)]
OptionalText200 = Annotated[str, StringConstraints(strip_whitespace=True, max_length=200)]
Phone = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    AfterValidator(_digits),
    StringConstraints(min_length=10, max_length=13),
]
Cnpj = Annotated[
    str,
    StringConstraints(strip_whitespace=True),
    AfterValidator(_digits),
    StringConstraints(min_length=14, max_length=14),
    AfterValidator(_check_cnpj),
]
HexColor = Annotated[
    str, StringConstraints(strip_whitespace=True, to_upper=True, pattern=r"^#[0-9A-Fa-f]{6}$")
]
Slug = Annotated[
    str,
    BeforeValidator(lambda value: value.strip().lower() if isinstance(value, str) else value),
    StringConstraints(pattern=r"^[a-z0-9](?:[a-z0-9-]{1,58}[a-z0-9])$"),
    AfterValidator(_check_slug),
]
PriceValue = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]
Price = Annotated[PriceValue, Field(ge=0, max_digits=10, decimal_places=2)]
