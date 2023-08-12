from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Literal, TypeVar

from sqlalchemy import Engine
from sqlalchemy.orm import Session

import host.ureg
from host import currency
from host.gameplay_settings import GameplaySettings
from host.nation import models
from host.nation.ministry import Ministry
from host.nation.types.basic import Population
from host.nation.types.interior import Infrastructure, Technology, Land

if TYPE_CHECKING:
    from host.nation import Nation

InfrastructureMessages = Literal[
    "infrastructure_cost", "buy_infrastructure_success", "buy_infrastructure_failure", "infrastructure_cashback",
    "insufficient_cashback", "insufficient_infrastructure", "sell_infrastructure_success"
]

BuyMessages = Literal[
    "infrastructure_buy_success", "insufficient_funds", "infrastructure_cashback_success", "insufficient_"
]

K = TypeVar("K")

CashbackModifier = 0.5


class Interior(Ministry):
    __slots__ = "_player", "_engine"

    def __init__(self, nation: Nation, engine: Engine):
        self._player = nation
        self._engine = engine

    @cached_property
    def _interior(self) -> models.InteriorModel:
        with Session(self._engine) as session:
            interior = session.query(models.InteriorModel).filter_by(user_id=self._player.identifier).first()
            if interior is None:
                interior = models.InteriorModel(user_id=self._player.identifier, land=0)
                session.add(interior)
                session.commit()
            return interior

    @property
    def population(self) -> Population:
        return Population(self.infrastructure.amount * GameplaySettings["interior"]["population_per_infrastructure"])

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def revenue(self) -> currency.CurrencyRate:
        income_increase = 1 + self._player.boost("income_increase")
        return self._player.interior.population * GameplaySettings["interior"][
            "revenue_per_population"] * income_increase

    @cached_property
    def infrastructure(self) -> Infrastructure:
        return Infrastructure(self._player, self._interior, self._engine)

    @cached_property
    def technology(self) -> Technology:
        return Technology(self._player, self._interior, self._engine)

    @cached_property
    def land(self) -> Land:
        return Land(self._player, self._interior, self._engine)

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        bill = self.infrastructure.bill + self.technology.bill + self.land.bill
        return bill * (1 - self._player.boost("bill_modifier"))
