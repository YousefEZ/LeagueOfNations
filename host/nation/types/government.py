from __future__ import annotations

import json
from typing import Literal

from pydantic import BaseModel
from qalib.translators.element.types.embed import Colour

from host.nation.types.boosts import BoostsLookup

GovernmentTypes = Literal[
    "Anarchy",
    "Monarchy",
    "Democracy",
    "Dictatorship",
    "Republic",
    "Theocracy",
    "Fascism",
    "Communism",
    "Revolutionary",
]


class GovernmentSchema(BaseModel, frozen=True):
    name: GovernmentTypes
    emoji: str
    description: str
    boosts: BoostsLookup
    colour: Colour

with open("objects/governments.json", encoding="utf8", mode="r") as governments_file:
    Governments = {
        identifier: GovernmentSchema.model_validate(government)
        for identifier, government in json.load(governments_file).items()
    }
