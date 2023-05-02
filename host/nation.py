from __future__ import annotations

from functools import cached_property
from typing import get_args, List, Optional

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host.interior import Interior
from host.types import Ministries, Happiness, UserId
from host.ministry import Ministry
from host.bank import Bank
from host.models import MetadataModel
from host.trade import Trade


class Metadata:
    def __init__(self, identifier: UserId, engine: Engine):
        self._identifier = identifier
        self._engine = engine

    @cached_property
    def metadata(self) -> MetadataModel:
        with Session(self._engine) as session:
            metadata: Optional[MetadataModel] = session.query(MetadataModel).filter_by(user_id=self._identifier).first()
        if metadata is None:
            raise ValueError(f"Metadata does not exist for {self._identifier}")
        return metadata

    @property
    def nation_name(self) -> str:
        return self.metadata.nation


class Nation:
    def __init__(self, identifier: UserId, engine: Engine):
        self._identifier: UserId = identifier
        self._engine: Engine = engine

    @cached_property
    def identifier(self) -> UserId:
        return self._identifier

    @cached_property
    def metadata(self) -> Metadata:
        return Metadata(self._identifier, self._engine)

    @cached_property
    def bank(self) -> Bank:
        bank = Bank(self, self._engine)
        return bank

    @cached_property
    def trade(self) -> Trade:
        trade = Trade(self, self._engine)
        return trade

    @property
    def nation_name(self) -> str:
        metadata = self.metadata
        return metadata.nation_name

    @classmethod
    def start(cls, identifier: UserId, name: str, engine: Engine) -> Nation:
        metadata = MetadataModel(user_id=identifier, nation=name)

        with Session(engine) as session:
            session.add(metadata)
            session.commit()

        return cls(identifier, engine)

    def find_player(self, identifier: UserId) -> Nation:
        return Nation(identifier, self._engine)

    @cached_property
    def ministries(self) -> List[Ministry]:
        return [getattr(self, ministry) for ministry in get_args(Ministries)]

    @cached_property
    def interior(self) -> Interior:
        return Interior(self, self._engine)

    @property
    def happiness(self) -> Happiness:
        happiness: Happiness = sum((ministry.happiness for ministry in self.ministries), Happiness(0))
        return Happiness(happiness * self.happiness_modifier)

    @property
    def population(self) -> int:
        return self.interior.population

    @property
    def happiness_modifier(self) -> float:
        return 1.0 + sum(ministry.boost("happiness_modifier") for ministry in self.ministries)
