from __future__ import annotations

from pint import UnitRegistry

ureg = UnitRegistry()
ureg.define("LND = [currency]")

Currency = ureg.LND
CurrencyRate = ureg.LND / ureg.days
