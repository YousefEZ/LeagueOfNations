from __future__ import annotations

from abc import ABC

import host.base_types
import host.currency
import host.ureg
from host.nation import types


class Ministry(ABC):
    @property
    @host.ureg.Registry.wraps(host.currency.CurrencyRate, None)
    def bill(self) -> host.currency.CurrencyRate:
        return 0 * host.currency.CurrencyRate

    @property
    @host.ureg.Registry.wraps(host.currency.CurrencyRate, None)
    def revenue(self) -> host.currency.CurrencyRate:
        return 0 * host.currency.CurrencyRate

    @property
    def happiness(self) -> types.basic.Happiness:
        return types.basic.Happiness(0)

    # noinspection PyMethodMayBeStatic
    def boost(self) -> types.boosts.BoostsLookup:
        return types.boosts.BoostsLookup()
