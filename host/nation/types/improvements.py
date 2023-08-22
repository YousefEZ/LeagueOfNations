from __future__ import annotations

import json
from typing import List

from pydantic import BaseModel

from host.nation.types.boosts import BoostsLookup


class Improvement(BaseModel, frozen=True):
    name: str
    emoji: str
    description: str
    boosts: BoostsLookup
    dependencies: List[str]


with open("objects/improvements.json", encoding="utf8", mode="r") as improvements_file:
    Improvements = {identifier: Improvement.model_validate(improvement) for identifier, improvement in
                    json.load(improvements_file).items()}
