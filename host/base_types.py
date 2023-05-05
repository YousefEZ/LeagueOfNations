from __future__ import annotations

from typing import NewType

from pint import UnitRegistry

UserId = NewType("UserId", int)

ureg = UnitRegistry()
ureg.define("LND = [currency]")

Currency = ureg.LND
CurrencyRate = ureg.LND / ureg.seconds
