from __future__ import annotations

import logging
from functools import cached_property
from typing import TYPE_CHECKING, Literal, TypeVar, Protocol, Type, Generic

from pint.facets.plain import PlainQuantity
from sqlalchemy import Engine
from sqlalchemy.orm import Session

import host.ureg
from host import currency
from host.defaults import defaults
from host.gameplay_settings import GameplaySettings
from host.nation import models
from host.nation.ministry import Ministry
from host.nation.types.basic import Population
from host.nation.types.interior import (
    Data,
    InfrastructurePoints,
    TechnologyPoints,
    LandPoints,
)
from host.nation.types.transactions import PurchaseResult, SellResult

if TYPE_CHECKING:
    from host.nation import Nation

InfrastructureMessages = Literal[
    "infrastructure_cost",
    "buy_infrastructure_success",
    "buy_infrastructure_failure",
    "infrastructure_cashback",
    "insufficient_cashback",
    "insufficient_infrastructure",
    "sell_infrastructure_success",
]

BuyMessages = Literal[
    "infrastructure_buy_success",
    "insufficient_funds",
    "infrastructure_cashback_success",
    "insufficient_",
]

K = TypeVar("K")


class UnitExchangeProtocol(Protocol[K]):
    @property
    def amount(self) -> K:
        raise NotImplementedError

    def price_at(self, level: K) -> currency.Currency:
        raise NotImplementedError

    def price_order(self, amount: K) -> currency.Currency:
        raise NotImplementedError

    def bill_at(self, level: K) -> currency.CurrencyRate:
        raise NotImplementedError

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        raise NotImplementedError

    def buy(self, amount: K) -> PurchaseResult:
        raise NotImplementedError

    def sell(self, amount: K) -> SellResult:
        raise NotImplementedError

    @classmethod
    def load_player(cls, nation: Nation, interior: models.InteriorModel, session: Session) -> UnitExchangeProtocol[K]:
        raise NotImplementedError


def unit_exchange(cls: Type[Data[K]]) -> Type[UnitExchangeProtocol[K]]:
    class UnitExchange(Generic[K]):
        __slots__ = "_singleton", "_interior", "_nation", "_session"
        unit: Type[Data[K]] = cls

        def __init__(self, nation: Nation, interior: models.InteriorModel, session: Session):
            self._nation = nation
            self._interior = interior
            self._session = session

        @classmethod
        def load_player(cls, nation: Nation, interior: models.InteriorModel, session: Session) -> UnitExchange[K]:
            return cls(nation, interior, session)

        @host.ureg.Registry.wraps(currency.Currency, [None, None, None])
        def _get_unit_price_at(self, point: K, level: K) -> currency.Currency:
            return self.unit.PricePoints[point] * level + self.unit.FloorPrice

        @host.ureg.Registry.wraps(currency.Currency, [None, None])
        def price_at(self, level: K) -> currency.Currency:
            point = 0
            for point in self.unit.PricePoints:
                if level <= point:
                    return self._get_unit_price_at(point, level) * self.price_modifier
            return self._get_unit_price_at(point, level) * self.price_modifier

        @host.ureg.Registry.wraps(currency.Currency, [None, None])
        def price_order(self, amount: K) -> currency.Currency:
            return sum(
                (self.price_at(self.amount + i) for i in range(1, amount + 1)),
                currency.lnd(0),
            )

        @host.ureg.Registry.wraps(currency.CurrencyRate, [None, None, None])
        def _get_unit_bill_at(self, point: K, level: K) -> currency.CurrencyRate:
            return self.unit.BillPoints[point] * level.magnitude if isinstance(level, PlainQuantity) else level

        @host.ureg.Registry.wraps(currency.CurrencyRate, [None, None])
        def bill_at(self, level: K) -> currency.CurrencyRate:
            point = 0
            for point in self.unit.BillPoints:
                if level <= point:
                    return self._get_unit_bill_at(point, level)
            return self._get_unit_bill_at(point, level)

        @property
        def amount(self) -> K:
            return self.unit.get(self._interior)

        def _set_amount(self, value: K) -> None:
            logging.debug("Setting %s to %s", self.unit.__name__, value)
            self.unit.set(self._interior, value)
            self._session.commit()
            logging.debug("Set %s to %s", self.unit.__name__, value)

        @property
        def price_modifier(self) -> float:
            return 1 - getattr(self._nation.boost, self.unit.PriceModifier)

        @property
        def bill_modifier(self) -> float:
            return 1 - getattr(self._nation.boost, self.unit.BillModifier)

        def buy(self, amount: K) -> PurchaseResult:
            assert amount > 0, "Amount must be positive"
            price: currency.Currency = self.price_order(amount)
            if not self._nation.bank.enough_funds(price):
                return PurchaseResult.INSUFFICIENT_FUNDS
            self._nation.bank.deduct(price)
            self._set_amount(self.amount + amount)
            return PurchaseResult.SUCCESS

        def sell(self, amount: K) -> SellResult:
            assert amount > 0, "Amount must be positive"
            if self.amount < amount:
                return SellResult.INSUFFICIENT_AMOUNT
            self._nation.bank.add(self.price_order(amount) * GameplaySettings.interior.cashback_modifier)
            self._set_amount(self.amount - amount)
            return SellResult.SUCCESS

        @property
        @host.ureg.Registry.wraps(currency.CurrencyRate, None)
        def bill(self) -> currency.CurrencyRate:
            return self.bill_at(self.amount) * self.bill_modifier

    return UnitExchange


Infrastructure = unit_exchange(InfrastructurePoints)
Technology = unit_exchange(TechnologyPoints)
Land = unit_exchange(LandPoints)


class Interior(Ministry):
    __slots__ = "_player", "_session"

    def __init__(self, nation: Nation, session: Session):
        self._player = nation
        self._session = session

    @property
    def _interior(self) -> models.InteriorModel:
        interior = self._session.query(models.InteriorModel).filter_by(user_id=self._player.identifier).first()
        if interior is None:
            interior = models.InteriorModel(
                user_id=self._player.identifier,
                land=GameplaySettings.interior.starter_land,
                infrastructure=GameplaySettings.interior.starter_infrastructure,
                technology=GameplaySettings.interior.starter_technology,
                spent_technology=0,
            )
            self._session.add(interior)
            self._session.commit()
        return interior

    @property
    def population(self) -> Population:
        return Population(self.infrastructure.amount * GameplaySettings.interior.population_per_infrastructure)

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def revenue(self) -> currency.CurrencyRate:
        gdb_per_capita = GameplaySettings.interior.revenue_per_population + self._player.boost.income_increase
        income_modifier = 1 + self._player.boost.income_modifier
        return self.population * gdb_per_capita * income_modifier

    @cached_property
    def infrastructure(self) -> Infrastructure:
        return Infrastructure.load_player(self._player, self._interior, self._session)

    @cached_property
    def technology(self) -> Technology:
        return Technology.load_player(self._player, self._interior, self._session)

    @cached_property
    def land(self) -> Land:
        return Land.load_player(self._player, self._interior, self._session)

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        bill = self.infrastructure.bill + self.technology.bill + self.land.bill
        return bill * (1 - self._player.boost.bill_modifier)
