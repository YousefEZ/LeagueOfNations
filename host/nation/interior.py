from __future__ import annotations

from collections import OrderedDict
from functools import cached_property
from typing import TYPE_CHECKING, Literal, Generic, TypeVar, Protocol, Type

from sqlalchemy import Engine
from sqlalchemy.orm import Session

import host.ureg
from host import currency
from host.nation import models
from host.nation.ministry import Ministry
from host.nation.types.basic import InfrastructureUnit, LandUnit, TechnologyUnit
from host.nation.types.boosts import PriceModifierBoosts, BillModifierBoosts

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


class Data(Protocol[K]):
    PriceModifier: PriceModifierBoosts
    FloorPrice: currency.Currency
    PricePoints: OrderedDict[K, currency.Currency]
    BillModifier: BillModifierBoosts
    FloorBill: currency.CurrencyRate
    BillPoints: OrderedDict[K, currency.CurrencyRate]

    @staticmethod
    def get(interior: models.InteriorModel) -> K:
        raise NotImplementedError

    @staticmethod
    def set(interior: models.InteriorModel, value: K) -> None:
        raise NotImplementedError


class Calculator(Generic[K]):

    def __init__(self, cls: Data):
        self._data = cls

    @host.ureg.Registry.wraps(currency.Currency, None)
    def _get_unit_price_at(self, point: K, level: K) -> currency.Currency:
        return self._data.PricePoints[point] * level + self._data.FloorPrice

    @host.ureg.Registry.wraps(currency.Currency, None)
    def price_at(self, level: K) -> currency.Currency:
        previous_point = 0
        for point, price in self._data.PricePoints.items():
            if level <= point:
                return self._get_unit_price_at(previous_point, level)
            previous_point = point
        return self._get_unit_price_at(previous_point, level)

    @host.ureg.Registry.wraps(currency.Currency, None)
    def price_order(self, current_level: K, amount: K) -> currency.Currency:
        return sum((self.price_at(current_level + i) for i in range(amount)), currency.Currency(0))

    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def _get_unit_bill_at(self, point: K, level: K) -> currency.CurrencyRate:
        return self._data.BillPoints[point] * level

    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill_at(self, level: K) -> currency.CurrencyRate:
        previous_point = 0
        for point, price in self._data.PricePoints.items():
            if level <= point:
                return self._get_unit_bill_at(previous_point, level)
            previous_point = point
        return self._get_unit_bill_at(previous_point, level)


class CalculatorProtocol(Protocol[K]):

    @property
    def amount(self) -> K:
        raise NotImplementedError

    @host.ureg.Registry.wraps(currency.Currency, None)
    def price_at(self, level: K) -> currency.Currency:
        raise NotImplementedError

    def buy(self, amount: K) -> bool:
        raise NotImplementedError

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        raise NotImplementedError


def calculator(cls: Data[K]) -> CalculatorProtocol[K]:
    class SingletonCalculator(cls):
        def __init__(self):
            super().__init__(cls)

    class WrapperCalculator(CalculatorProtocol[K]):
        __slots__ = "_singleton", "_interior", "_nation", "_engine"
        singleton: Type[Data[K], Calculator[K]] = SingletonCalculator()

        def __init__(self, nation: Nation, interior: models.InteriorModel, engine: Engine):
            self._nation = nation
            self._interior = interior
            self._engine = engine

        @property
        def amount(self) -> K:
            return self.singleton.get(self._interior)

        def _set_amount(self, value: K) -> None:
            with Session(self._engine) as session:
                self.singleton.set(self._interior, value)
                session.add(self._interior)
                session.commit()

        @property
        def price_modifier(self) -> float:
            return 1 - self._nation.boost(cls.PriceModifier)

        @property
        def bill_modifier(self) -> float:
            return 1 - self._nation.boost(cls.BillModifier)

        @host.ureg.Registry.wraps(currency.Currency, None)
        def price_at(self, level: K) -> currency.Currency:
            return self.singleton.price_at(level) * self.price_modifier

        @host.ureg.Registry.wraps(currency.Currency, None)
        def price_order(self, amount: K) -> currency.Currency:
            return self.singleton.price_order(self.amount, amount) * self.price_modifier

        def buy(self, amount: K) -> bool:
            if amount <= 0:
                return False
            price = self.price_order(amount)
            if self._nation.bank.enough_funds(price):
                return False
            self._nation.bank.deduct(price)
            self._set_amount(self.amount + amount)
            return True

        @property
        @host.ureg.Registry.wraps(currency.CurrencyRate, None)
        def bill(self) -> currency.CurrencyRate:
            return WrapperCalculator.singleton.bill_at(self.amount) * self.bill_modifier

    return WrapperCalculator


@calculator
class Infrastructure(Calculator[InfrastructureUnit]):
    PriceModifier = "infrastructure_cost_modifier"
    FloorPrice = currency.Currency(500)
    PricePoints = OrderedDict([
        (InfrastructureUnit(20), currency.Currency(12)),
        (InfrastructureUnit(100), currency.Currency(15)),
        (InfrastructureUnit(200), currency.Currency(20)),
        (InfrastructureUnit(1_000), currency.Currency(25)),
        (InfrastructureUnit(3_000), currency.Currency(30)),
        (InfrastructureUnit(4_000), currency.Currency(40)),
        (InfrastructureUnit(5_000), currency.Currency(60)),
        (InfrastructureUnit(8_000), currency.Currency(70)),
        (InfrastructureUnit(15_000), currency.Currency(80)),
    ])
    BillModifier = "infrastructure_bill_modifier"
    FloorBill = currency.CurrencyRate(20)
    BillPoints = OrderedDict([
        (InfrastructureUnit(100), currency.CurrencyRate(0.04)),
        (InfrastructureUnit(200), currency.CurrencyRate(0.05)),
        (InfrastructureUnit(300), currency.CurrencyRate(0.06)),
        (InfrastructureUnit(500), currency.CurrencyRate(0.07)),
        (InfrastructureUnit(700), currency.CurrencyRate(0.08)),
        (InfrastructureUnit(1_000), currency.CurrencyRate(0.09)),
        (InfrastructureUnit(2_000), currency.CurrencyRate(0.11)),
        (InfrastructureUnit(3_000), currency.CurrencyRate(0.13)),
        (InfrastructureUnit(4_000), currency.CurrencyRate(0.15)),
        (InfrastructureUnit(5_000), currency.CurrencyRate(0.17)),
        (InfrastructureUnit(8_000), currency.CurrencyRate(0.1725)),
        (InfrastructureUnit(32_000), currency.CurrencyRate(0.175)),
        (InfrastructureUnit(35_000), currency.CurrencyRate(0.15)),
        (InfrastructureUnit(37_000), currency.CurrencyRate(0.14)),
        (InfrastructureUnit(40_000), currency.CurrencyRate(0.13)),
    ])

    @staticmethod
    def get(interior: models.InteriorModel) -> InfrastructureUnit:
        return interior.infrastructure

    @staticmethod
    def set(interior: models.InteriorModel, value: InfrastructureUnit) -> None:
        interior.infrastructure = value


@calculator
class Land(Calculator[LandUnit]):
    PriceModifier = "land_cost_modifier"
    FloorPrice: currency.Currency = currency.Currency(400)
    PricePoints: OrderedDict[LandUnit, currency.Currency] = OrderedDict([
        (LandUnit(20), currency.Currency(1.5)),
        (LandUnit(30), currency.Currency(2)),
        (LandUnit(40), currency.Currency(2.5)),
        (LandUnit(100), currency.Currency(3)),
        (LandUnit(150), currency.Currency(3.5)),
        (LandUnit(200), currency.Currency(5)),
        (LandUnit(250), currency.Currency(10)),
        (LandUnit(300), currency.Currency(15)),
        (LandUnit(400), currency.Currency(20)),
        (LandUnit(500), currency.Currency(25)),
        (LandUnit(800), currency.Currency(30)),
        (LandUnit(1_200), currency.Currency(35)),
        (LandUnit(2_000), currency.Currency(40)),
        (LandUnit(3_000), currency.Currency(45)),
        (LandUnit(4_000), currency.Currency(55)),
        (LandUnit(8_000), currency.Currency(75))
    ])
    BillModifier = "land_bill_modifier"
    FloorBill: currency.Currency = currency.CurrencyRate(0.3)
    BillPoints: OrderedDict[LandUnit, currency.CurrencyRate] = OrderedDict([
        (LandUnit(20), currency.CurrencyRate(0.001)),
        (LandUnit(30), currency.CurrencyRate(0.002)),
        (LandUnit(40), currency.CurrencyRate(0.003)),
        (LandUnit(100), currency.CurrencyRate(0.004)),
        (LandUnit(150), currency.CurrencyRate(0.005)),
        (LandUnit(200), currency.CurrencyRate(0.006)),
        (LandUnit(250), currency.CurrencyRate(0.007)),
        (LandUnit(300), currency.CurrencyRate(0.008)),
        (LandUnit(400), currency.CurrencyRate(0.009)),
        (LandUnit(500), currency.CurrencyRate(0.01)),
        (LandUnit(800), currency.CurrencyRate(0.011)),
        (LandUnit(1_200), currency.CurrencyRate(0.012)),
        (LandUnit(2_000), currency.CurrencyRate(0.013)),
        (LandUnit(3_000), currency.CurrencyRate(0.014)),
        (LandUnit(4_000), currency.CurrencyRate(0.015)),
        (LandUnit(8_000), currency.CurrencyRate(0.016))
    ])

    @staticmethod
    def get(interior: models.InteriorModel) -> LandUnit:
        return interior.land

    @staticmethod
    def set(interior: models.InteriorModel, value: LandUnit) -> None:
        interior.land = value


@calculator
class Technology(Calculator[TechnologyUnit]):
    PriceModifier = "technology_cost_modifier"
    FloorPrice = currency.Currency(0)
    PricePoints = OrderedDict([
        (TechnologyUnit(0), currency.Currency(4_000)),
        (TechnologyUnit(10), currency.Currency(12_000)),
        (TechnologyUnit(50), currency.Currency(16_000)),
        (TechnologyUnit(100), currency.Currency(25_000)),
        (TechnologyUnit(200), currency.Currency(30_000)),
        (TechnologyUnit(400), currency.Currency(40_000)),
        (TechnologyUnit(800), currency.Currency(60_000)),
        (TechnologyUnit(1_500), currency.Currency(70_000)),
        (TechnologyUnit(5_000), currency.Currency(80_000)),
        (TechnologyUnit(10_000), currency.Currency(90_000)),
        (TechnologyUnit(20_000), currency.Currency(100_000)),
        (TechnologyUnit(150_000), currency.Currency(120_000))
    ])
    BillModifier = "technology_bill_modifier"
    FloorBill = currency.CurrencyRate(10)
    BillPoints = OrderedDict([
        (TechnologyUnit(0), currency.CurrencyRate(0.01)),
        (TechnologyUnit(10), currency.CurrencyRate(0.02)),
        (TechnologyUnit(50), currency.CurrencyRate(0.03)),
        (TechnologyUnit(100), currency.CurrencyRate(0.04)),
        (TechnologyUnit(200), currency.CurrencyRate(0.05)),
        (TechnologyUnit(400), currency.CurrencyRate(0.06)),
        (TechnologyUnit(800), currency.CurrencyRate(0.07)),
        (TechnologyUnit(1_500), currency.CurrencyRate(0.08)),
        (TechnologyUnit(5_000), currency.CurrencyRate(0.09)),
        (TechnologyUnit(10_000), currency.CurrencyRate(0.1)),
        (TechnologyUnit(20_000), currency.CurrencyRate(0.11)),
        (TechnologyUnit(150_000), currency.CurrencyRate(0.12))
    ])

    @staticmethod
    def get(interior: models.InteriorModel) -> TechnologyUnit:
        return interior.technology

    @staticmethod
    def set(interior: models.InteriorModel, value: TechnologyUnit) -> None:
        interior.technology = value


class Interior(Ministry):
    __slots__ = "_nation", "_engine"

    def __init__(self, nation: Nation, engine: Engine):
        self._nation = nation
        self._engine = engine

    @cached_property
    def _interior(self) -> models.InteriorModel:
        with Session(self._engine) as session:
            interior = session.query(models.InteriorModel).filter_by(user_id=self._nation.identifier).first()
            if interior is None:
                interior = models.InteriorModel(user_id=self._nation.identifier, land=0)
                session.add(interior)
                session.commit()
            return interior

    @cached_property
    def infrastructure(self) -> Infrastructure:
        return Infrastructure(self._nation, self._interior, self._engine)

    @cached_property
    def technology(self) -> Technology:
        return Technology(self._nation, self._interior, self._engine)

    @cached_property
    def land(self) -> Land:
        return Land(self._nation, self._interior, self._engine)

    @property
    @host.ureg.Registry.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        bill = self.infrastructure.bill + self.technology.bill + self.land.bill
        return bill * (1 - self._nation.boost("bill_modifier"))
