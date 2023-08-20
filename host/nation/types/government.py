from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel

from host.nation.types.boosts import BoostsLookup

GovernmentTypes = Literal["Democracy", "Monarchy", "Dictatorship", "Communism", "Anarchy"]


class Government(BaseModel, frozen=True):
    name: GovernmentTypes
    emoji: str
    description: str
    boosts: BoostsLookup


with open("object/governments.json", "r") as governments_file:
    Governments = {identifier: Government.model_validate(government) for identifier, government in
                   json.load(governments_file).items()}
