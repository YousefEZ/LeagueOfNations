from __future__ import annotations

from abc import ABC

from host.currency import (
    as_currency,
    as_daily_currency_rate,
    as_daily_price_rate,
    as_price,
)
from host.nation import types


class Ministry(ABC):

    @property
    @as_daily_price_rate
    @as_price
    def bill(self) -> int:
        return 0

    @property
    @as_daily_currency_rate
    @as_currency
    def revenue(self) -> int:
        return 0

    @property
    def happiness(self) -> types.basic.Happiness:
        return types.basic.Happiness(0)

    # noinspection PyMethodMayBeStatic
    def boost(self) -> types.boosts.BoostsLookup:
        return types.boosts.BoostsLookup()
