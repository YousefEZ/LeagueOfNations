from __future__ import annotations

from abc import ABC

from host.currency import DailyCurrencyRate, wraps
from host.nation import types


class Ministry(ABC):
    @property
    @wraps(DailyCurrencyRate, (None,))
    def bill(self) -> int:
        return 0

    @property
    @wraps(DailyCurrencyRate, (None,))
    def revenue(self) -> int:
        return 0

    @property
    def happiness(self) -> types.basic.Happiness:
        return types.basic.Happiness(0)

    # noinspection PyMethodMayBeStatic
    def boost(self) -> types.boosts.BoostsLookup:
        return types.boosts.BoostsLookup()
