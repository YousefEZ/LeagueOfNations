from __future__ import annotations

from typing import Literal, TypedDict
from typing_extensions import NotRequired

Boosts = Literal["happiness_modifier", "income_modifier", "income_increase", "bill_modifier", "bill_reduction"]


class BoostsLookup(TypedDict):
    happiness_modifier: NotRequired[float]
    income_increase: NotRequired[float]
    income_modifier: NotRequired[float]
    bill_modifier: NotRequired[float]
    bill_reduction: NotRequired[float]


default_boosts: BoostsLookup = {
    "happiness_modifier": 0.0,
    "income_increase": 0.0,
    "income_modifier": 0.0,
    "bill_modifier": 0.0,
    "bill_reduction": 0.0,
}
