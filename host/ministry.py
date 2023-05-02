from __future__ import annotations

from abc import ABC

from host.types import ureg, CurrencyRate, Happiness, Boosts, default_boosts


class Ministry(ABC):

    @property
    @ureg.wraps(CurrencyRate, None)
    def expenditure(self) -> CurrencyRate:
        return 0 * CurrencyRate

    @property
    def happiness(self) -> Happiness:
        return Happiness(0)

    # noinspection PyMethodMayBeStatic
    def boost(self, boost: Boosts) -> float:
        return default_boosts[boost]
