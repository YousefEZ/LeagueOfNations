from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, TypedDict

from host.nation.types.boosts import BoostsLookup

GovernmentTypes = Literal["Democracy", "Monarchy", "Dictatorship", "Communism", "Anarchy"]


@dataclass(frozen=True, slots=True)
class Government:
    name: GovernmentTypes
    emoji: str
    description: str
    boosts: BoostsLookup
