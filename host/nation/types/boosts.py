from __future__ import annotations

from typing import Literal, TypedDict
from typing_extensions import NotRequired

PriceModifierBoosts = Literal[
    "infrastructure_cost_modifier",
    "technology_cost_modifier",
    "land_cost_modifier",
]

BillModifierBoosts = Literal[
    "infrastructure_bill_modifier",
    "technology_bill_modifier",
    "land_bill_modifier",
]

Boosts = Literal[
    "happiness_modifier",
    "income_modifier",
    "income_increase",
    "bill_modifier",
    "bill_reduction",
    PriceModifierBoosts,
    BillModifierBoosts
]


class BoostsLookup(TypedDict):
    happiness_modifier: NotRequired[float]
    income_increase: NotRequired[float]
    income_modifier: NotRequired[float]
    infrastructure_cost_modifier: NotRequired[float]
    infrastructure_bill_modifier: NotRequired[float]
    technology_cost_modifier: NotRequired[float]
    technology_bill_modifier: NotRequired[float]
    land_cost_modifier: NotRequired[float]
    land_bill_modifier: NotRequired[float]
    bill_modifier: NotRequired[float]
    bill_reduction: NotRequired[float]


default_boosts: BoostsLookup = {
    "happiness_modifier": 0.0,
    "income_increase": 0.0,
    "income_modifier": 0.0,
    "infrastructure_cost_modifier": 0.0,
    "infrastructure_bill_modifier": 0.0,
    "technology_cost_modifier": 0.0,
    "technology_bill_modifier": 0.0,
    "land_cost_modifier": 0.0,
    "land_bill_modifier": 0.0,
    "bill_modifier": 0.0,
    "bill_reduction": 0.0,
}
