from __future__ import annotations

from host.ureg import Registry

Registry.define("LND = [currency]")
Currency = Registry.LND
CurrencyRate = Registry.LND / Registry.days


@Registry.wraps(Currency, None)
def lnd(value: Registry.LND) -> Currency:
    return value * Currency


@Registry.wraps(CurrencyRate, None)
def lnd_rate(value: Registry.LND / Registry.days) -> CurrencyRate:
    return value * CurrencyRate
