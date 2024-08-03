from __future__ import annotations

from datetime import datetime
from typing import NewType

import jinja2.runtime
from babel import numbers

from host.currency import Currency, CurrencyRate
from host.ureg import Registry

UserId = NewType("UserId", int)


def variable_guard(func):
    def wrapper(*args, **kwargs):
        if any(isinstance(arg, jinja2.runtime.Undefined) for arg in args):
            return ""
        return func(*args, **kwargs)

    return wrapper


@variable_guard
@Registry.wraps(None, Currency)
def render_currency(value: Currency) -> str:
    return numbers.format_compact_currency(value, currency="USD", locale="en_US", fraction_digits=3)


@variable_guard
@Registry.wraps(None, CurrencyRate)
def render_currency_rate(value: Currency) -> str:
    magnitude = numbers.format_compact_currency(value, currency="USD", locale="en_US", fraction_digits=3)
    return f"{magnitude} / day"


@variable_guard
def render_date(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")
