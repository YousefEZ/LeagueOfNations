from __future__ import annotations

from typing import Literal, TypedDict

from host.nation.types.boosts import BoostsLookup

GovernmentTypes = Literal["Democracy", "Monarchy", "Dictatorship", "Communism", "Anarchy"]


class Government(TypedDict):
    name: GovernmentTypes
    emoji: str
    description: str
    boosts: BoostsLookup
