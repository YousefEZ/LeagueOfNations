from __future__ import annotations

from collections import OrderedDict
from typing import Protocol, Optional, Type, TypeVar

from host.currency import Currency, CurrencyRate, daily_currency_rate
from host.nation import models
from host.nation.types.basic import InfrastructureUnit, LandUnit, TechnologyUnit
from host.nation.types.boosts import PriceModifierBoosts, BillModifierBoosts

K = TypeVar("K")


class Data(Protocol[K]):
    PriceModifier: PriceModifierBoosts
    FloorPrice: Currency
    PricePoints: OrderedDict[K, Currency]
    BillModifier: BillModifierBoosts
    FloorBill: CurrencyRate
    BillPoints: OrderedDict[K, CurrencyRate]
    Unit: Type[K]

    @staticmethod
    def get(interior: models.InteriorModel) -> K:
        raise NotImplementedError

    @staticmethod
    def set(interior: models.InteriorModel, value: K) -> None:
        raise NotImplementedError

    @staticmethod
    def singleton() -> Data[K]:
        raise NotImplementedError


class InfrastructurePoints(Data[InfrastructureUnit]):
    _singleton: Optional[InfrastructurePoints] = None
    PriceModifier: PriceModifierBoosts = "infrastructure_cost_modifier"
    FloorPrice = Currency(500)
    PricePoints = OrderedDict(
        [
            (InfrastructureUnit(20), Currency(12)),
            (InfrastructureUnit(100), Currency(15)),
            (InfrastructureUnit(200), Currency(20)),
            (InfrastructureUnit(1_000), Currency(25)),
            (InfrastructureUnit(3_000), Currency(30)),
            (InfrastructureUnit(4_000), Currency(40)),
            (InfrastructureUnit(5_000), Currency(60)),
            (InfrastructureUnit(8_000), Currency(70)),
            (InfrastructureUnit(15_000), Currency(80)),
        ]
    )
    BillModifier: BillModifierBoosts = "infrastructure_bill_modifier"
    FloorBill = daily_currency_rate(Currency(20))
    BillPoints = OrderedDict(
        [
            (InfrastructureUnit(100), daily_currency_rate(Currency(0.04))),
            (InfrastructureUnit(200), daily_currency_rate(Currency(0.05))),
            (InfrastructureUnit(300), daily_currency_rate(Currency(0.06))),
            (InfrastructureUnit(500), daily_currency_rate(Currency(0.07))),
            (InfrastructureUnit(700), daily_currency_rate(Currency(0.08))),
            (InfrastructureUnit(1_000), daily_currency_rate(Currency(0.09))),
            (InfrastructureUnit(2_000), daily_currency_rate(Currency(0.11))),
            (InfrastructureUnit(3_000), daily_currency_rate(Currency(0.13))),
            (InfrastructureUnit(4_000), daily_currency_rate(Currency(0.15))),
            (InfrastructureUnit(5_000), daily_currency_rate(Currency(0.17))),
            (InfrastructureUnit(8_000), daily_currency_rate(Currency(0.1725))),
            (InfrastructureUnit(32_000), daily_currency_rate(Currency(0.175))),
            (InfrastructureUnit(35_000), daily_currency_rate(Currency(0.15))),
            (InfrastructureUnit(37_000), daily_currency_rate(Currency(0.14))),
            (InfrastructureUnit(40_000), daily_currency_rate(Currency(0.13))),
        ]
    )
    Unit = InfrastructureUnit

    @staticmethod
    def get(interior: models.InteriorModel) -> InfrastructureUnit:
        return InfrastructureUnit(interior.infrastructure)

    @staticmethod
    def set(interior: models.InteriorModel, value: InfrastructureUnit) -> None:
        interior.infrastructure = value

    @staticmethod
    def singleton() -> InfrastructurePoints:
        if InfrastructurePoints._singleton is None:
            InfrastructurePoints._singleton = InfrastructurePoints()
        return InfrastructurePoints._singleton


class LandPoints(Data[LandUnit]):
    _singleton: Optional[LandPoints] = None
    PriceModifier: PriceModifierBoosts = "land_cost_modifier"
    FloorPrice: Currency = Currency(400)
    PricePoints: OrderedDict[LandUnit, Currency] = OrderedDict(
        [
            (LandUnit(20), Currency(1.5)),
            (LandUnit(30), Currency(2)),
            (LandUnit(40), Currency(2.5)),
            (LandUnit(100), Currency(3)),
            (LandUnit(150), Currency(3.5)),
            (LandUnit(200), Currency(5)),
            (LandUnit(250), Currency(10)),
            (LandUnit(300), Currency(15)),
            (LandUnit(400), Currency(20)),
            (LandUnit(500), Currency(25)),
            (LandUnit(800), Currency(30)),
            (LandUnit(1_200), Currency(35)),
            (LandUnit(2_000), Currency(40)),
            (LandUnit(3_000), Currency(45)),
            (LandUnit(4_000), Currency(55)),
            (LandUnit(8_000), Currency(75)),
        ]
    )
    BillModifier: BillModifierBoosts = "land_bill_modifier"
    FloorBill: CurrencyRate = daily_currency_rate(Currency(0.3))
    BillPoints: OrderedDict[LandUnit, CurrencyRate] = OrderedDict(
        [
            (LandUnit(20), daily_currency_rate(Currency(0.001))),
            (LandUnit(30), daily_currency_rate(Currency(0.002))),
            (LandUnit(40), daily_currency_rate(Currency(0.003))),
            (LandUnit(100), daily_currency_rate(Currency(0.004))),
            (LandUnit(150), daily_currency_rate(Currency(0.005))),
            (LandUnit(200), daily_currency_rate(Currency(0.006))),
            (LandUnit(250), daily_currency_rate(Currency(0.007))),
            (LandUnit(300), daily_currency_rate(Currency(0.008))),
            (LandUnit(400), daily_currency_rate(Currency(0.009))),
            (LandUnit(500), daily_currency_rate(Currency(0.01))),
            (LandUnit(800), daily_currency_rate(Currency(0.011))),
            (LandUnit(1_200), daily_currency_rate(Currency(0.012))),
            (LandUnit(2_000), daily_currency_rate(Currency(0.013))),
            (LandUnit(3_000), daily_currency_rate(Currency(0.014))),
            (LandUnit(4_000), daily_currency_rate(Currency(0.015))),
            (LandUnit(8_000), daily_currency_rate(Currency(0.016))),
        ]
    )
    Unit = LandUnit

    @staticmethod
    def get(interior: models.InteriorModel) -> LandUnit:
        return LandUnit(interior.land)

    @staticmethod
    def set(interior: models.InteriorModel, value: LandUnit) -> None:
        interior.land = value

    @staticmethod
    def singleton() -> LandPoints:
        if LandPoints._singleton is None:
            LandPoints._singleton = LandPoints()
        return LandPoints._singleton


class TechnologyPoints(Data[TechnologyUnit]):
    _singleton: Optional[TechnologyPoints] = None
    PriceModifier: PriceModifierBoosts = "technology_cost_modifier"
    FloorPrice = Currency(0)
    PricePoints = OrderedDict(
        [
            (TechnologyUnit(0), Currency(4_000)),
            (TechnologyUnit(10), Currency(12_000)),
            (TechnologyUnit(50), Currency(16_000)),
            (TechnologyUnit(100), Currency(25_000)),
            (TechnologyUnit(200), Currency(30_000)),
            (TechnologyUnit(400), Currency(40_000)),
            (TechnologyUnit(800), Currency(60_000)),
            (TechnologyUnit(1_500), Currency(70_000)),
            (TechnologyUnit(5_000), Currency(80_000)),
            (TechnologyUnit(10_000), Currency(90_000)),
            (TechnologyUnit(20_000), Currency(100_000)),
            (TechnologyUnit(150_000), Currency(120_000)),
        ]
    )
    BillModifier: BillModifierBoosts = "technology_bill_modifier"
    FloorBill = daily_currency_rate(Currency(10))
    BillPoints = OrderedDict(
        [
            (TechnologyUnit(0), daily_currency_rate(Currency(0.01))),
            (TechnologyUnit(10), daily_currency_rate(Currency(0.02))),
            (TechnologyUnit(50), daily_currency_rate(Currency(0.03))),
            (TechnologyUnit(100), daily_currency_rate(Currency(0.04))),
            (TechnologyUnit(200), daily_currency_rate(Currency(0.05))),
            (TechnologyUnit(400), daily_currency_rate(Currency(0.06))),
            (TechnologyUnit(800), daily_currency_rate(Currency(0.07))),
            (TechnologyUnit(1_500), daily_currency_rate(Currency(0.08))),
            (TechnologyUnit(5_000), daily_currency_rate(Currency(0.09))),
            (TechnologyUnit(10_000), daily_currency_rate(Currency(0.1))),
            (TechnologyUnit(20_000), daily_currency_rate(Currency(0.11))),
            (TechnologyUnit(150_000), daily_currency_rate(Currency(0.12))),
        ]
    )
    Unit = TechnologyUnit

    @staticmethod
    def get(interior: models.InteriorModel) -> TechnologyUnit:
        return TechnologyUnit(interior.technology)

    @staticmethod
    def set(interior: models.InteriorModel, value: TechnologyUnit) -> None:
        interior.technology = value

    @staticmethod
    def singleton() -> TechnologyPoints:
        if TechnologyPoints._singleton is None:
            TechnologyPoints._singleton = TechnologyPoints()
        return TechnologyPoints._singleton
