from __future__ import annotations

import json
from functools import cached_property
from typing import TYPE_CHECKING, Literal, Dict, get_args

from pint import Quantity
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import base_types
from host.nation.ministry import Ministry

if TYPE_CHECKING:
    from host.nation import Nation, models, types

InfrastructureMessages = Literal["infrastructure_built", "insufficient_funds", "insufficient_resources"]
ImprovementMessages = Literal[
    "not_enough_improvements", "negative_quantity", "improvement_sold", "improvement_bought", "insufficient_funds",
    "exceeding_maximum_quantity"
]

with open("object/improvements.json", "r") as improvements_file:
    Improvements = json.load(improvements_file)


class Improvement:
    __slots__ = "_improvement", "_player", "_engine"

    resale_rate: float = 0.5

    def __init__(self, improvement: models.ImprovementsModel, player: Nation, engine: Engine):
        self._improvement = improvement
        self._player = player
        self._engine = engine

    @property
    def improvement(self) -> types.Improvement:
        return Improvements[self._improvement.name]

    @classmethod
    def create(cls, improvement_type: types.ImprovementTypes, player: Nation, engine: Engine) -> Improvement:
        with Session(engine) as session:
            improvement = models.ImprovementsModel(user_id=player.identifier, name=improvement_type, quantity=0)
            session.add(improvement)
            session.commit()
            return cls(improvement, player, engine)

    @property
    @base_types.ureg.wraps(base_types.Currency, None)
    def price(self) -> Quantity:
        return base_types.ureg.Quantity(self.improvement["price"], base_types.Currency)

    @property
    @base_types.ureg.wraps(base_types.CurrencyRate, None)
    def cost(self) -> Quantity:
        return self.improvement["cost"] * self._improvement.quantity * base_types.CurrencyRate

    def _buy(self, quantity: int) -> None:
        self._player.bank.deduct(self.price * quantity)
        self._improvement.quantity += quantity
        with Session(self._engine) as session:
            session.commit()

    def buy(self, quantity: int) -> ImprovementMessages:
        if quantity < 0:
            return "negative_quantity"
        if self._improvement.quantity + quantity <= self.improvement["max_quantity"]:
            return "exceeding_maximum_quantity"
        if self._player.bank.funds < self.price * quantity:
            return "insufficient_funds"
        self._buy(quantity)
        return "improvement_bought"

    def _sell(self, quantity: int) -> None:
        self._player.bank.add(self.price * quantity * self.resale_rate)
        self._improvement.quantity -= quantity
        with Session(self._engine) as session:
            session.commit()

    def sell(self, quantity: int) -> ImprovementMessages:
        if quantity < 0:
            return "negative_quantity"
        if self._improvement.quantity < quantity:
            return "not_enough_improvements"
        self._sell(quantity)
        return "improvement_sold"

    def boost(self, boost: types.Boosts) -> float:
        return self.improvement["boosts"].get(boost, 0.0) * self._improvement.quantity


ImprovementsLookup = Dict[types.ImprovementTypes, Improvement]


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
                interior = models.InteriorModel(user_id=self._player.identifier, infrastructure=0, land=0)
                session.add(interior)
                session.commit()
            return interior

    @cached_property
    def _improvements(self) -> ImprovementsLookup:
        with Session(self._engine) as session:
            improvements = session.query(models.ImprovementsModel).filter_by(user_id=self._player.identifier).all()
            return {improvement.name: Improvement(improvement, self._player, self._engine)
                    for improvement in improvements}

    def get(self, improvement: types.ImprovementTypes) -> Improvement:
        if improvement not in get_args(types.ImprovementTypes):
            raise ValueError(f"Improvement type {improvement} not found")
        if improvement not in self._improvements:
            self._improvements[improvement] = Improvement.create(improvement, self._player, self._engine)
        return self._improvements[improvement]

    @property
    @base_types.ureg.wraps(base_types.CurrencyRate, None)
    def bill(self) -> Quantity:
        return base_types.ureg.Quantity(0, base_types.CurrencyRate)

    @property
    def infrastructure(self) -> types.Infrastructure:
        return types.Infrastructure(0)

    @base_types.ureg.wraps(base_types.Currency, None)
    def infrastructure_cost(self, quantity: int) -> Quantity:
        return 1000 * base_types.Currency * self.infrastructure * quantity

    @property
    def population(self) -> types.Population:
        return types.Population(0)

    def build_infrastructure(self, quantity: int) -> InfrastructureMessages:
        cost = self.infrastructure_cost(quantity)
        if not self._player.bank.enough_funds(cost):
            return "insufficient_funds"
        self._player.bank.deduct(cost)
        return "infrastructure_built"
