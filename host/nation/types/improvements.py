from __future__ import annotations

import json
from typing import Dict

import pydantic
from pydantic import BaseModel

from host import currency
from host.gameplay_settings import GameplaySettings
from host.nation.types.boosts import BoostsLookup


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
    def price(self) -> currency.Currency:
        return currency.Currency(self.raw_price)

    @property
    def cashback(self) -> currency.Currency:
        return currency.Currency(self.raw_price * GameplaySettings.interior.cashback_modifier)


with open("objects/improvements.json", encoding="utf8", mode="r") as improvements_file:
    Improvements = {
        identifier: ImprovementSchema.model_validate(improvement)
        for identifier, improvement in json.load(improvements_file).items()
    }
