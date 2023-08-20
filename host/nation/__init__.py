from __future__ import annotations

from functools import cached_property
from typing import List, get_args

from sqlalchemy.orm import Session

import host.ureg
from host import base_types, currency
from host.defaults import defaults
from host.gameplay_settings import GameplaySettings
from host.nation import types, models
from host.nation.bank import Bank
from host.nation.foreign import Foreign
from host.nation.interior import Interior
from host.nation.meta import Meta
from host.nation.ministry import Ministry
from host.nation.trade import Trade
from host.nation.types.basic import Population


class Nation:
    def __init__(self, identifier: base_types.UserId, session: Session):
        self._identifier: base_types.UserId = identifier
        self._session: Session = session

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
    def trade(self) -> Trade:
        return Trade(self, self._session)

    @cached_property
    def interior(self) -> Interior:
        return Interior(self, self._session)

    @cached_property
    def foreign(self) -> Foreign:
        return Foreign(self, self._session)

    @cached_property
    def ministries(self) -> List[Ministry]:
        return [getattr(self, ministry_object) for ministry_object in get_args(types.ministries.Ministries)]

    @classmethod
    def start(cls, identifier: base_types.UserId, name: str, engine: Session) -> Nation:
        metadata = models.MetadataModel(user_id=identifier, nation=name, flag=defaults.meta.flag)

        with Session(engine) as session:
            session.add(metadata)
            session.commit()

        return cls(identifier, engine)

    def find_player(self, identifier: base_types.UserId) -> Nation:
        return Nation(identifier, self._session)

    @property
    def happiness(self) -> types.basic.Happiness:
        happiness: types.basic.Happiness = sum((ministry_object.happiness for ministry_object in self.ministries),
                                               types.basic.Happiness(0))
        return types.basic.Happiness(happiness * self.happiness_modifier)

    @property
    def population(self) -> Population:
        return Population(self.interior.infrastructure.amount * GameplaySettings.interior.population_per_infrastructure)

    @property
    def population_modifier(self) -> float:
        return 1 + self.boost.population_modifier / 100

    @property
    def happiness_modifier(self) -> float:
        return 1 + self.boost.happiness_modifier / 100

    @property
    def boost(self) -> types.boosts.BoostsLookup:
        return types.boosts.BoostsLookup.combine(*[ministry_object.boost() for ministry_object in self.ministries])

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def revenue(self) -> currency.CurrencyRate:
        happiness = self.happiness
        population = self.population
        return happiness * 3 * population * currency.CurrencyRate
