from __future__ import annotations

from typing import Literal, NamedTuple, TypedDict, Dict

from host.nation.types.boosts import BoostsLookup

ResourceTypes = Literal[
    "Cattle", "Fish", "Fruit", "Pigs", "Wheat", "Aluminum", "Coal", "Iron", "Lead", "Oil", "Uranium", "Bread", "Cheese",
    "Fruit Juice", "Meat", "Milk"
]


class ResourcePair(NamedTuple):
    primary: ResourceTypes
    secondary: ResourceTypes


class Resource(TypedDict):
    emoji: str
    description: str
    boosts: BoostsLookup


Resources = Dict[ResourceTypes, Resource]
