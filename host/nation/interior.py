from __future__ import annotations

from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Literal, List, Optional

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import currency
from host.nation import types, models
from host.nation.ministry import Ministry

if TYPE_CHECKING:
    from host.nation import Nation

InfrastructureMessages = Literal["infrastructure_built", "insufficient_funds", "insufficient_resources"]
ImprovementMessages = Literal[
    "not_enough_improvements", "negative_quantity", "improvement_sold", "improvement_bought", "insufficient_funds",
    "exceeding_maximum_quantity"
]


class BuildRequest:

    def __init__(self, building: types.interior.BuildingTypes, amount: int, start_time: Optional[datetime] = None):
        self._building = building
        self._amount = amount
        self._start_time = start_time or datetime.now()

    def create_request(self) -> models.BuildRequestModel:
        ...


class Interior(Ministry):
    __slots__ = "_player", "_engine"

    def __init__(self, player: Nation, engine: Engine):
        self._player = player
        self._engine = engine

    @cached_property
    def interior(self) -> models.InteriorModel:
        with Session(self._engine) as session:
            interior = session.query(models.InteriorModel).filter_by(user_id=self._player.identifier).first()
            if interior is None:
                interior = models.InteriorModel(user_id=self._player.identifier, land=0)
                session.add(interior)
                session.commit()
            return interior

    @property
    @currency.ureg.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        return 0 * currency.CurrencyRate

    @property
    def infrastructure(self) -> List[models.InfrastructureModel]:
        with Session(self._engine) as session:
            return session.query(models.InfrastructureModel).filter_by(user_id=self._player.identifier).all()

    @currency.ureg.wraps(currency.Currency, [None, None])
    def infrastructure_cost(self, quantity: int) -> currency.Currency:
        return 1000 * currency.Currency * self.infrastructure * quantity

    @property
    def population(self) -> types.basic.Population:
        return types.basic.Population(0)

    def build_infrastructure(self, quantity: int) -> InfrastructureMessages:
        cost = self.infrastructure_cost(quantity)
        if not self._player.bank.enough_funds(cost):
            return "insufficient_funds"
        self._player.bank.deduct(cost)
        return "infrastructure_built"
