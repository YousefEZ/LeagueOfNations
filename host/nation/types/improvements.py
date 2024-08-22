from __future__ import annotations

import json
from typing import Dict

import pydantic
from host import currency
from host.gameplay_settings import GameplaySettings
from host.nation.types.boosts import BoostsLookup
from pydantic import BaseModel


class ImprovementSchema(BaseModel, frozen=True):
    name: str
    emoji: str
    description: str
    url: str
    limit: int
    raw_price: int = pydantic.Field(alias="price")
    boosts: BoostsLookup
    dependencies: Dict[str, int]

    @property
    @currency.as_price
    def price(self) -> int:
        return self.raw_price

    @property
    @currency.as_currency
    def cashback(self) -> float:
        return self.raw_price * GameplaySettings.interior.cashback_modifier


with open("objects/improvements.json", encoding="utf8", mode="r") as improvements_file:
    Improvements: Dict[str, ImprovementSchema] = {
        identifier: ImprovementSchema.model_validate(improvement)
        for identifier, improvement in json.load(improvements_file).items()
    }
