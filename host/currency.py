from __future__ import annotations

from host.ureg import Registry

Registry.define("LND = [currency]")
Currency = Registry.LND
CurrencyRate = Registry.LND / Registry.days
