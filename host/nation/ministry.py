from __future__ import annotations

from abc import ABC

import host.base_types
from host import base_types
from host.nation import types


class Ministry(ABC):

    @property
    @base_types.ureg.wraps(base_types.CurrencyRate, None)
    def bill(self) -> base_types.CurrencyRate:
        return 0 * base_types.CurrencyRate

    @property
    @base_types.ureg.wraps(base_types.CurrencyRate, None)
    def revenue(self) -> base_types.CurrencyRate:
        return 0 * base_types.CurrencyRate

    @property
    def happiness(self) -> types.Happiness:
        return types.Happiness(0)

    # noinspection PyMethodMayBeStatic
    def boost(self, boost: types.Boosts) -> float:
        return types.default_boosts[boost]
