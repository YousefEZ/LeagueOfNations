from __future__ import annotations

from typing import NewType

from babel import numbers

from host.currency import Currency, CurrencyRate
from host.ureg import Registry

UserId = NewType("UserId", int)


@Registry.wraps(None, Currency)
def render_currency(value: Currency) -> str:
    return numbers.format_compact_currency(value, currency="USD", locale="en_US", fraction_digits=3)


@Registry.wraps(None, CurrencyRate)
def render_currency_rate(value: Currency) -> str:
    magnitude = numbers.format_compact_currency(value, currency="USD", locale="en_US", fraction_digits=3)
    return f"{magnitude} / day"
