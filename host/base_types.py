from __future__ import annotations

from datetime import datetime
from typing import NewType

import jinja2.runtime

from host.currency import Currency, CurrencyRate

UserId = NewType("UserId", int)


def variable_guard(func):
    def wrapper(*args, **kwargs):
        if any(isinstance(arg, jinja2.runtime.Undefined) for arg in args):
            return ""
        return func(*args, **kwargs)

    return wrapper


def render_currency(value: Currency) -> str:
    return str(value)


def render_currency_rate(value: CurrencyRate) -> str:
    return str(value)


@variable_guard
def render_date(value: datetime) -> str:
    return value.strftime("%d/%m/%Y %H:%M")
