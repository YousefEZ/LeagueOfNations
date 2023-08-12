from __future__ import annotations

from typing import Literal, TypedDict

from pydantic import BaseModel

from host.nation.types.boosts import BoostsLookup

GovernmentTypes = Literal["Democracy", "Monarchy", "Dictatorship", "Communism", "Anarchy"]


class Government(BaseModel, frozen=True):
    name: GovernmentTypes
    emoji: str
    description: str
    boosts: BoostsLookup
