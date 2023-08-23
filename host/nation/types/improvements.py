from __future__ import annotations

import json
from typing import List

import pydantic
from pydantic import BaseModel, computed_field

from host import currency
from host.nation.types.boosts import BoostsLookup


class Improvement(BaseModel, frozen=True):
    name: str
    emoji: str
    description: str
    limit: int
    raw_price: int = pydantic.Field(alias="price")
    boosts: BoostsLookup
    dependencies: List[str]

    @property
    def price(self) -> currency.Currency:
        return currency.lnd(self.raw_price)


with open("objects/improvements.json", encoding="utf8", mode="r") as improvements_file:
    Improvements = {identifier: Improvement.model_validate(improvement) for identifier, improvement in
                    json.load(improvements_file).items()}
