from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING, Literal, TypeVar, Generic

from sqlalchemy import Engine
from sqlalchemy.orm import Session

import host.ureg
from host import currency
from host.defaults import defaults
from host.gameplay_settings import GameplaySettings
from host.nation import models
from host.nation.ministry import Ministry
from host.nation.types.basic import Population, InfrastructureUnit, LandUnit, TechnologyUnit
from host.nation.types.interior import Data, InfrastructurePoints, TechnologyPoints, LandPoints, PurchaseResult, \
    SellResult

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


class UnitExchange(Generic[K]):
    __slots__ = "_singleton", "_interior", "_nation", "_engine"
    unit: Data[K]

    def __init__(self, nation: Nation, interior: models.InteriorModel, engine: Engine):
        self._nation = nation
        self._interior = interior
        self._engine = engine

    @host.ureg.Registry.wraps(currency.Currency, [None, None, None])
    def _get_unit_price_at(self, point: K, level: K) -> currency.Currency:
        return self.unit.PricePoints[point] * level + self.unit.FloorPrice

    @host.ureg.Registry.wraps(currency.Currency, [None, None])
    def price_at(self, level: K) -> currency.Currency:
        previous_point = 0
        for point, price in self.unit.PricePoints.items():
            if level <= point:
                return self._get_unit_price_at(previous_point, level) * self.price_modifier
            previous_point = point
        return self._get_unit_price_at(previous_point, level) * self.price_modifier

    @host.ureg.Registry.wraps(currency.Currency, [None, None])
    def price_order(self, amount: K) -> currency.Currency:
        return sum((self.price_at(self.amount + i) for i in range(amount)), currency.Currency(0)) * self.price_modifier

    @host.ureg.Registry.wraps(currency.CurrencyRate, [None, None, None])
    def _get_unit_bill_at(self, point: K, level: K) -> currency.CurrencyRate:
        return self.unit.BillPoints[point] * level

    @host.ureg.Registry.wraps(currency.CurrencyRate, [None, None])
    def bill_at(self, level: K) -> currency.CurrencyRate:
        previous_point = 0
        for point, price in self.unit.PricePoints.items():
            if level <= point:
                return self._get_unit_bill_at(previous_point, level)
            previous_point = point
        return self._get_unit_bill_at(previous_point, level)

    @property
    def amount(self) -> K:
        return self.unit.get(self._interior)

    def _set_amount(self, value: K) -> None:
        with Session(self._engine) as session:
            self.unit.set(self._interior, value)
            session.add(self._interior)
            session.commit()

    @property
    def price_modifier(self) -> float:
        return 1 - getattr(self._nation.boost, self.unit.PriceModifier)

    @property
    def bill_modifier(self) -> float:
        return 1 - getattr(self._nation.boost, self.unit.BillModifier)

    def buy(self, amount: K) -> PurchaseResult:
        if amount <= 0:
            return PurchaseResult.NEGATIVE_AMOUNT
        price = self.price_order(amount)
        if self._nation.bank.enough_funds(price):
            return PurchaseResult.INSUFFICIENT_FUNDS
        self._nation.bank.deduct(price)
        self._set_amount(self.amount + amount)
        return PurchaseResult.SUCCESS

    def sell(self, amount: K) -> SellResult:
        if amount <= 0:
            return SellResult.NEGATIVE_AMOUNT
        if self.amount < amount:
            return SellResult.INSUFFICIENT_AMOUNT
        self._nation.bank.add(self.price_order(amount) * defaults.interior.cashback_modifier)
        self._set_amount(self.amount - amount)
        return SellResult.SUCCESS

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        return self.bill_at(self.amount) * self.bill_modifier


class Infrastructure(UnitExchange[InfrastructureUnit]):
    unit = InfrastructurePoints


class Technology(UnitExchange[TechnologyUnit]):
    unit = TechnologyPoints


class Land(UnitExchange[LandUnit]):
    unit = LandPoints


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
        return Population(self.infrastructure.amount * GameplaySettings.interior.population_per_infrastructure)

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def revenue(self) -> currency.CurrencyRate:
        income_increase = 1 + self._player.boost.income_increase
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
        return bill * (1 - self._player.boost.bill_modifier)
