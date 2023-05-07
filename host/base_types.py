from __future__ import annotations

from typing import NewType

from babel import numbers

from host.currency import ureg, Currency, CurrencyRate

UserId = NewType("UserId", int)


@ureg.wraps(None, Currency)
def render_currency(value: Currency) -> str:
    return numbers.format_compact_currency(value, currency="USD", locale="en_US", fraction_digits=3)


@ureg.wraps(None, CurrencyRate)
def render_currency_rate(value: Currency) -> str:
    magnitude = numbers.format_compact_currency(value, currency="USD", locale="en_US", fraction_digits=3)
    return f"{magnitude} / day"
