from __future__ import annotations

from functools import cached_property
from typing import get_args, List

from pint import Quantity
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import models, types
from host.interior import Interior
from host.ministry import Ministry
from host.bank import Bank
from host.trade import Trade


class Metadata:
    def __init__(self, identifier: types.UserId, engine: Engine):
        self._identifier = identifier
        self._engine = engine

    @cached_property
    def metadata(self) -> models.MetadataModel:
        with Session(self._engine) as session:
            metadata = session.query(models.MetadataModel).filter_by(user_id=self._identifier).first()
        if metadata is None:
            raise ValueError(f"Metadata does not exist for {self._identifier}")
        return metadata

    @property
    def nation_name(self) -> str:
        return self.metadata.nation


class Nation:
    def __init__(self, identifier: types.UserId, engine: Engine):
        self._identifier: types.UserId = identifier
        self._engine: Engine = engine

    @cached_property
    def identifier(self) -> types.UserId:
        return self._identifier

    @property
    def name(self) -> str:
        return self.metadata.nation_name

    @cached_property
    def metadata(self) -> Metadata:
        return Metadata(self._identifier, self._engine)

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
    def ministries(self) -> List[Ministry]:
        return [getattr(self, ministry) for ministry in get_args(types.Ministries)]

    @classmethod
    def start(cls, identifier: types.UserId, name: str, engine: Engine) -> Nation:
        metadata = models.MetadataModel(user_id=identifier, nation=name)

        with Session(engine) as session:
            session.add(metadata)
            session.commit()

        return cls(identifier, engine)

    def find_player(self, identifier: types.UserId) -> Nation:
        return Nation(identifier, self._engine)

    @property
    def happiness(self) -> types.Happiness:
        happiness: types.Happiness = sum(ministry.happiness for ministry in self.ministries)
        return types.Happiness(happiness * self.happiness_modifier)

    @property
    def population(self) -> int:
        return self.interior.population

    @property
    def happiness_modifier(self) -> float:
        return 1 + self.boost("happiness_modifier") / 100

    def boost(self, boost: types.Boosts) -> float:
        return sum(ministry.boost(boost) for ministry in self.ministries)

    @property
    @types.ureg.wraps(types.CurrencyRate, None)
    def revenue(self) -> Quantity:
        happiness = self.happiness
        population = self.population
        return happiness * 3 * population * types.CurrencyRate
