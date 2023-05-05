from __future__ import annotations

from typing import NamedTuple, TypedDict, Dict, Literal, NewType

from typing_extensions import NotRequired

Ministries = Literal["Bank", "Trade", "Interior", "Foreign"]
Boosts = Literal["happiness_modifier", "income_modifier", "income_increase", "bill_modifier", "bill_reduction"]

Infrastructure = NewType("Infrastructure", int)
Happiness = NewType("Happiness", float)
Population = NewType("Population", int)

ResourceTypes = Literal[
    "Cattle", "Fish", "Fruit", "Pigs", "Wheat", "Aluminum", "Coal", "Iron", "Lead", "Oil", "Uranium", "Bread", "Cheese",
    "Fruit Juice", "Meat", "Milk"
]

ImprovementTypes = Literal[
    "School", "Hospital", "Clinic", "Theater", "Stadium", "Factory", "Bank", "Supermarket", "Shopping Mall",
]

GovernmentTypes = Literal["Democracy", "Monarchy", "Dictatorship", "Communism", "Anarchy"]


class Government(TypedDict):
    name: GovernmentTypes
    emoji: str
    description: str
    boosts: BoostsLookup


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
