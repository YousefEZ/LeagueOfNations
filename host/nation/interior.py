from __future__ import annotations

import datetime
import uuid
from datetime import timedelta
from functools import cached_property
from typing import TYPE_CHECKING, Literal, Dict

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import currency, base_types
from host.nation import types, models
from host.nation.ministry import Ministry
from host.notifier import Notifier, Notification

if TYPE_CHECKING:
    from host.nation import Nation

InfrastructureMessages = Literal[
    "infrastructure_built", "insufficient_funds", "insufficient_resources", "already_constructing", "build_request_sent"
]


class BuildRequest:
    __slots__ = "_model", "_engine"

    def __init__(self, model: models.BuildRequestModel, engine: Engine):
        self._model = model
        self._engine = engine

    @property
    def id(self) -> str:
        return self._model.build_id

    @property
    def user(self) -> base_types.UserId:
        return base_types.UserId(self._model.user_id)

    @property
    def building(self) -> types.interior.Building:
        return types.interior.get_building(self._model.building, self._model.amount)

    @property
    def completed(self) -> bool:
        return datetime.datetime.now() >= self.completion

    @property
    def remaining_time(self) -> timedelta:
        if self.completed:
            return timedelta()
        return datetime.datetime.now() - self.completion

    @property
    def completion(self) -> datetime.datetime:
        return self._model.start + self.building.build_time

    @classmethod
    def make_request(cls, building: types.interior.Building, engine: Engine) -> BuildRequest:
        model = models.BuildRequestModel(
            user_id=str(int(uuid.uuid4())),
            building=building.name,
            quantity=building.amount
        )
        return cls(model, engine)


class Interior(Ministry):
    __slots__ = "_player", "_engine"

    def __init__(self, player: Nation, engine: Engine):
        self._player = player
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
    @currency.ureg.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        return sum(building.bill for building in self.infrastructure.values())

    @property
    def infrastructure(self) -> Dict[types.interior.BuildingTypes, types.interior.Building]:
        with Session(self._engine) as session:
            infrastructure = session.query(models.InfrastructureModel).filter_by(user_id=self._player.identifier).all()
            return {
                model.building: types.interior.get_building(model.building, model.amount) for model in infrastructure
            }

    @property
    def constructing(self) -> bool:
        with Session(self._engine) as session:
            query = session.query(models.BuildRequestModel).filter_by(user_id=self._player.identifier)
            return query.count() > 0

    @property
    def population(self) -> types.basic.Population:
        population = sum(building.population for building in self.infrastructure.values()
                         if isinstance(building, types.interior.Housing))

        return types.basic.Population(population)

    @property
    def employed(self) -> types.basic.Employment:
        employment = sum(building.employment for building in self.infrastructure.values()
                         if isinstance(building, types.interior.EmployableBuilding))
        population = self.population
        return types.basic.Employment(population if population < employment else employment)

    @property
    def literacy(self) -> types.basic.Literacy:
        literacy = sum(building.literacy for building in self.infrastructure.values()
                       if isinstance(building, types.interior.Education))

        rate = self.population / literacy
        return types.basic.Literacy(rate)

    @property
    def life_expectancy(self) -> types.basic.LifeExpectancy:
        health = sum(building.health for building in self.infrastructure.values()
                     if isinstance(building, types.interior.Health))
        life_expectancy = health / 20
        return types.basic.LifeExpectancy(life_expectancy)

    def build(self, building: types.interior.Building) -> InfrastructureMessages:
        if not self._player.bank.enough_funds(building.price):
            return "insufficient_funds"

        if self.constructing:
            return "already_constructing"
        self._player.bank.deduct(building.price)
        request = BuildRequest.make_request(building, self._engine)
        notification = Notification(self._player.identifier, request.completion, "building_complete",
                                    {"user": self._player.identifier, "request": request.id})
        Notifier(self._engine).schedule(notification)
        return "build_request_sent"
