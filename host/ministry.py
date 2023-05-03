from __future__ import annotations

from abc import ABC

from host import types


class Ministry(ABC):

    @property
    @types.ureg.wraps(types.CurrencyRate, None)
    def bill(self) -> types.CurrencyRate:
        return 0 * types.CurrencyRate

    @property
    @types.ureg.wraps(types.CurrencyRate, None)
    def revenue(self) -> types.CurrencyRate:
        return 0 * types.CurrencyRate

    @property
    def happiness(self) -> types.Happiness:
        return types.Happiness(0)

    # noinspection PyMethodMayBeStatic
    def boost(self, boost: types.Boosts) -> float:
        return types.default_boosts[boost]
