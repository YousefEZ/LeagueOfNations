from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

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


class BoostsLookup(BaseModel, frozen=True):
    happiness_modifier: float = Field(default=0.0)
    income_increase: float = Field(default=0.0)
    income_modifier: float = Field(default=0.0)
    infrastructure_cost_modifier: float = Field(default=0.0)
    infrastructure_bill_modifier: float = Field(default=0.0)
    technology_cost_modifier: float = Field(default=0.0)
    technology_bill_modifier: float = Field(default=0.0)
    land_cost_modifier: float = Field(default=0.0)
    land_bill_modifier: float = Field(default=0.0)
    bill_modifier: float = Field(default=0.0)
    bill_reduction: float = Field(default=0.0)


default_boosts = BoostsLookup()
