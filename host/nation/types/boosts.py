from __future__ import annotations

from typing import List, Literal

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
    BillModifierBoosts,
]


class BoostsLookup(BaseModel, frozen=True):
    happiness_modifier: float = Field(default=0.0, title="Happiness Modifier")
    income_increase: float = Field(default=0.0, title="Income Increase")
    income_modifier: float = Field(default=0.0, title="Income Modifier")
    infrastructure_cost_modifier: float = Field(default=0.0, title="Infrastructure Cost Modifier")
    infrastructure_bill_modifier: float = Field(default=0.0, title="Infrastructure Bill Modifier")
    technology_cost_modifier: float = Field(default=0.0, title="Technology Cost Modifier")
    technology_bill_modifier: float = Field(default=0.0, title="Technology Bill Modifier")
    land_cost_modifier: float = Field(default=0.0, title="Land Cost Modifier")
    land_bill_modifier: float = Field(default=0.0, title="Land Bill Modifier")
    bill_modifier: float = Field(default=0.0, title="Bill Modifier")
    bill_reduction: float = Field(default=0.0, title="Bill Reduction")
    population_modifier: float = Field(default=0.0, title="Population Modifier")

    def multiply(self, multiplier: float) -> BoostsLookup:
        return BoostsLookup(**{attr: value * multiplier for attr, value in vars(self).items()})

    def inverse(self) -> BoostsLookup:
        return BoostsLookup(**{attr: value * -1 for attr, value in vars(self).items()})

    @classmethod
    def combine(cls, *others: BoostsLookup) -> BoostsLookup:
        return cls(
            **{
                attr: sum(getattr(other, attr) for other in others)
                for attr in cls.model_json_schema()["properties"].keys()
            }
        )

    def pretty_print(self) -> List[str]:
        return [
            f"{value.title}: {'+' if boost > 0 else ''}{round(boost * 100, 2)}"
            for key, value in self.model_fields.items()
            if (boost := getattr(self, key))
        ]

    def __add__(self, other: BoostsLookup) -> BoostsLookup:
        return BoostsLookup(
            **{attr: value + getattr(other, attr) for attr, value in vars(self).items()}
        )


default_boosts = BoostsLookup()
