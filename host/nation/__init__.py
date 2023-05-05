from __future__ import annotations

from functools import cached_property
from typing import List, get_args

from pint import Quantity
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import base_types
from host.nation import types, models
from host.nation.bank import Bank
from host.nation.foreign import Foreign
from host.nation.interior import Interior
from host.nation.meta import Meta
from host.nation.meta import Meta
from host.nation.ministry import Ministry
from host.nation.trade import Trade


class Nation:
    def __init__(self, identifier: base_types.UserId, engine: Engine):
        self._identifier: base_types.UserId = identifier
        self._engine: Engine = engine

    @cached_property
    def identifier(self) -> base_types.UserId:
        return self._identifier

    @property
    def name(self) -> str:
        return self.metadata.nation_name

    @cached_property
    def metadata(self) -> Meta:
        return Meta(self._identifier, self._engine)

    @cached_property
    def bank(self) -> Bank:
        return Bank(self, self._engine)

    @cached_property
    def trade(self) -> Trade:
        return Trade(self, self._engine)

    @cached_property
    def interior(self) -> Interior:
        return Interior(self, self._engine)

    @cached_property
    def foreign(self) -> Foreign:
        return Foreign(self, self._engine)

    @cached_property
    def ministries(self) -> List[Ministry]:
        return [getattr(self, ministry_object) for ministry_object in get_args(types.Ministries)]

    @classmethod
    def start(cls, identifier: base_types.UserId, name: str, engine: Engine) -> Nation:
        metadata = models.MetadataModel(user_id=identifier, nation=name)

        with Session(engine) as session:
            session.add(metadata)
            session.commit()

        return cls(identifier, engine)

    def find_player(self, identifier: base_types.UserId) -> Nation:
        return Nation(identifier, self._engine)

    @property
    def happiness(self) -> types.Happiness:
        happiness: types.Happiness = sum(ministry_object.happiness for ministry_object in self.ministries)
        return types.Happiness(happiness * self.happiness_modifier)

    @property
    def population(self) -> int:
        return self.interior.population

    @property
    def happiness_modifier(self) -> float:
        return 1 + self.boost("happiness_modifier") / 100

    def boost(self, boost: types.Boosts) -> float:
        return sum(ministry_object.boost(boost) for ministry_object in self.ministries)

    @property
    @base_types.ureg.wraps(base_types.CurrencyRate, None)
    def revenue(self) -> Quantity:
        happiness = self.happiness
        population = self.population
        return happiness * 3 * population * base_types.CurrencyRate
