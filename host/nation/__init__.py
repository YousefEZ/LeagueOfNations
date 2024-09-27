from __future__ import annotations

from datetime import UTC, datetime
from enum import IntEnum, auto
from functools import cached_property
from typing import List, Optional, get_args

from host import base_types
from host.currency import as_currency, as_daily_currency_rate
from host.defaults import defaults
from host.gameplay_settings import GameplaySettings
from host.nation import models, types
from host.nation.bank import Bank
from host.nation.foreign import Foreign
from host.nation.government import Government
from host.nation.improvements import PublicWorks
from host.nation.interior import Interior
from host.nation.meta import Meta
from host.nation.ministry import Ministry
from host.nation.trade import Trade
from host.nation.types.basic import Population
from sqlalchemy.orm import Session


class StartResponses(IntEnum):
    SUCCESS = 0
    ALREADY_EXISTS = auto()
    NAME_TAKEN = auto()
    NAME_TOO_SHORT = auto()
    NAME_TOO_LONG = auto()
    NON_ASCII = auto()


def user_exists(identifier: base_types.UserId, session: Session) -> bool:
    metadata = session.query(models.MetadataModel).filter_by(user_id=identifier).first()
    return metadata is not None


class Nation:
    def __init__(self, identifier: base_types.UserId, session: Session):
        self._identifier: base_types.UserId = identifier
        self._session: Session = session

    @property
    def exists(self) -> bool:
        return user_exists(self._identifier, self._session)

    @staticmethod
    def search_for_nations(
        name: str, session: Session, with_like: bool = False
    ) -> List[models.MetadataModel]:
        if with_like:
            return (
                session.query(models.MetadataModel)
                .filter(models.MetadataModel.nation.like(f"%{name}%"))
                .all()
            )
        return session.query(models.MetadataModel).filter(models.MetadataModel.nation == name).all()

    @classmethod
    def fetch_from_name(cls, name: str, session: Session) -> Optional[Nation]:
        nation = cls.search_for_nations(name, session)
        if not nation:
            return None
        return cls(base_types.UserId(nation[0].user_id), session)

    @cached_property
    def identifier(self) -> base_types.UserId:
        return self._identifier

    @property
    def name(self) -> str:
        return self.metadata.nation_name

    @cached_property
    def metadata(self) -> Meta:
        return Meta(self._identifier, self._session)

    @cached_property
    def bank(self) -> Bank:
        return Bank(self, self._session)

    @cached_property
    def government(self) -> Government:
        return Government(self, self._session)

    @cached_property
    def trade(self) -> Trade:
        return Trade(self, self._session)

    @cached_property
    def interior(self) -> Interior:
        return Interior(self, self._session)

    @cached_property
    def public_works(self) -> PublicWorks:
        return PublicWorks(self, self._session)

    @cached_property
    def foreign(self) -> Foreign:
        return Foreign(self, self._session)

    @cached_property
    def ministries(self) -> List[Ministry]:
        return [
            getattr(self, ministry_object)
            for ministry_object in get_args(types.ministries.Ministries)
        ]

    @staticmethod
    def start(identifier: base_types.UserId, name: str, session: Session) -> StartResponses:
        if not name.isascii():
            return StartResponses.NON_ASCII

        if len(name) < GameplaySettings.metadata.minimum_nation_name_length:
            return StartResponses.NAME_TOO_SHORT

        if len(name) > GameplaySettings.metadata.maximum_nation_name_length:
            return StartResponses.NAME_TOO_LONG

        if user_exists(identifier, session):
            return StartResponses.ALREADY_EXISTS

        if Nation.fetch_from_name(name, session) is not None:
            return StartResponses.NAME_TAKEN
        metadata = models.MetadataModel(
            user_id=identifier,
            nation=name,
            emoji=defaults.meta.emoji,
            flag=defaults.meta.flag,
            created=datetime.now(UTC),
        )

        session.add(metadata)
        session.commit()

        return StartResponses.SUCCESS

    def find_player(self, identifier: base_types.UserId) -> Nation:
        return Nation(identifier, self._session)

    @property
    def happiness(self) -> types.basic.Happiness:
        happiness: types.basic.Happiness = sum(
            (ministry_object.happiness for ministry_object in self.ministries),
            types.basic.Happiness(0),
        )
        return types.basic.Happiness(happiness * self.happiness_modifier)

    @property
    def strength(self) -> float:
        return 0.0

    @property
    def population(self) -> Population:
        return Population(
            self.interior.infrastructure.amount
            * GameplaySettings.interior.population_per_infrastructure
        )

    @property
    def population_modifier(self) -> float:
        return 1 + self.boost.population_modifier / 100

    @property
    def happiness_modifier(self) -> float:
        return 1 + self.boost.happiness_modifier / 100

    @property
    def boost(self) -> types.boosts.BoostsLookup:
        return types.boosts.BoostsLookup.combine(
            *[ministry_object.boost() for ministry_object in self.ministries]
        )

    @property
    @as_daily_currency_rate
    @as_currency
    def revenue(self) -> float:
        happiness = self.happiness
        population = self.population
        return happiness * 3 * population
