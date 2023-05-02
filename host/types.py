from __future__ import annotations

from typing import NamedTuple, TypedDict, Dict, Literal, NewType

from pint import UnitRegistry
from typing_extensions import NotRequired

Ministries = Literal["Bank", "Trade"]
Boosts = Literal["happiness_modifier", "daily_income", "income_modifier"]

Infrastructure = NewType("Infrastructure", int)
Happiness = NewType("Happiness", float)
UserId = NewType("UserId", int)
Population = NewType("Population", int)

ureg = UnitRegistry()
ureg.define("LND = [currency]")
Currency = ureg.LND
CurrencyRate = ureg.LND / ureg.seconds

ResourceTypes = Literal[
    "Cattle", "Fish", "Fruit", "Pigs", "Wheat", "Aluminum", "Coal", "Iron", "Lead", "Oil", "Uranium", "Bread", "Cheese",
    "Fruit Juice", "Meat", "Milk"
]

ImprovementTypes = Literal[
    "School", "Hospital", "Clinic", "Theater", "Stadium", "Factory", "Bank", "Supermarket", "Shopping Mall",
]


class BoostsLookup(TypedDict):
    happiness_modifier: NotRequired[float]
    daily_income: NotRequired[float]
    income_modifier: NotRequired[float]


default_boosts: BoostsLookup = {
    "happiness_modifier": 0.0,
    "daily_income": 0.0,
    "income_modifier": 0.0,
}


class ImprovementRequirement(TypedDict):
    name: ImprovementTypes
    quantity: int


class Improvement(TypedDict):
    name: ImprovementTypes
    price: float
    cost: float
    max_quantity: int
    description: str
    boosts: BoostsLookup
    requirements: NotRequired[Dict[ImprovementTypes, ImprovementRequirement]]


class ResourcePair(NamedTuple):
    primary: ResourceTypes
    secondary: ResourceTypes


class Resource(TypedDict):
    emoji: str
    description: str
    boosts: BoostsLookup


Resources = Dict[ResourceTypes, Resource]
