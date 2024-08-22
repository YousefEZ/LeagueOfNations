from __future__ import annotations

from collections import OrderedDict
from typing import Protocol, Optional, Type, TypeVar

from host.currency import Price, PriceRate, daily_price_rate
from host.nation import models
from host.nation.types.basic import InfrastructureUnit, LandUnit, TechnologyUnit
from host.nation.types.boosts import PriceModifierBoosts, BillModifierBoosts

K = TypeVar("K")


class Data(Protocol[K]):
    PriceModifier: PriceModifierBoosts
    FloorPrice: Price
    PricePoints: OrderedDict[K, Price]
    BillModifier: BillModifierBoosts
    FloorBill: PriceRate
    BillPoints: OrderedDict[K, PriceRate]
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
    FloorPrice = Price(500)
    PricePoints = OrderedDict(
        [
            (InfrastructureUnit(20), Price(12)),
            (InfrastructureUnit(100), Price(15)),
            (InfrastructureUnit(200), Price(20)),
            (InfrastructureUnit(1_000), Price(25)),
            (InfrastructureUnit(3_000), Price(30)),
            (InfrastructureUnit(4_000), Price(40)),
            (InfrastructureUnit(5_000), Price(60)),
            (InfrastructureUnit(8_000), Price(70)),
            (InfrastructureUnit(15_000), Price(80)),
        ]
    )
    BillModifier: BillModifierBoosts = "infrastructure_bill_modifier"
    FloorBill = daily_price_rate(Price(20))
    BillPoints = OrderedDict(
        [
            (InfrastructureUnit(100), daily_price_rate(Price(0.04))),
            (InfrastructureUnit(200), daily_price_rate(Price(0.05))),
            (InfrastructureUnit(300), daily_price_rate(Price(0.06))),
            (InfrastructureUnit(500), daily_price_rate(Price(0.07))),
            (InfrastructureUnit(700), daily_price_rate(Price(0.08))),
            (InfrastructureUnit(1_000), daily_price_rate(Price(0.09))),
            (InfrastructureUnit(2_000), daily_price_rate(Price(0.11))),
            (InfrastructureUnit(3_000), daily_price_rate(Price(0.13))),
            (InfrastructureUnit(4_000), daily_price_rate(Price(0.15))),
            (InfrastructureUnit(5_000), daily_price_rate(Price(0.17))),
            (InfrastructureUnit(8_000), daily_price_rate(Price(0.1725))),
            (InfrastructureUnit(32_000), daily_price_rate(Price(0.175))),
            (InfrastructureUnit(35_000), daily_price_rate(Price(0.15))),
            (InfrastructureUnit(37_000), daily_price_rate(Price(0.14))),
            (InfrastructureUnit(40_000), daily_price_rate(Price(0.13))),
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
    FloorPrice: Price = Price(400)
    PricePoints: OrderedDict[LandUnit, Price] = OrderedDict(
        [
            (LandUnit(20), Price(1.5)),
            (LandUnit(30), Price(2)),
            (LandUnit(40), Price(2.5)),
            (LandUnit(100), Price(3)),
            (LandUnit(150), Price(3.5)),
            (LandUnit(200), Price(5)),
            (LandUnit(250), Price(10)),
            (LandUnit(300), Price(15)),
            (LandUnit(400), Price(20)),
            (LandUnit(500), Price(25)),
            (LandUnit(800), Price(30)),
            (LandUnit(1_200), Price(35)),
            (LandUnit(2_000), Price(40)),
            (LandUnit(3_000), Price(45)),
            (LandUnit(4_000), Price(55)),
            (LandUnit(8_000), Price(75)),
        ]
    )
    BillModifier: BillModifierBoosts = "land_bill_modifier"
    FloorBill: PriceRate = daily_price_rate(Price(0.3))
    BillPoints: OrderedDict[LandUnit, PriceRate] = OrderedDict(
        [
            (LandUnit(20), daily_price_rate(Price(0.001))),
            (LandUnit(30), daily_price_rate(Price(0.002))),
            (LandUnit(40), daily_price_rate(Price(0.003))),
            (LandUnit(100), daily_price_rate(Price(0.004))),
            (LandUnit(150), daily_price_rate(Price(0.005))),
            (LandUnit(200), daily_price_rate(Price(0.006))),
            (LandUnit(250), daily_price_rate(Price(0.007))),
            (LandUnit(300), daily_price_rate(Price(0.008))),
            (LandUnit(400), daily_price_rate(Price(0.009))),
            (LandUnit(500), daily_price_rate(Price(0.01))),
            (LandUnit(800), daily_price_rate(Price(0.011))),
            (LandUnit(1_200), daily_price_rate(Price(0.012))),
            (LandUnit(2_000), daily_price_rate(Price(0.013))),
            (LandUnit(3_000), daily_price_rate(Price(0.014))),
            (LandUnit(4_000), daily_price_rate(Price(0.015))),
            (LandUnit(8_000), daily_price_rate(Price(0.016))),
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
    FloorPrice = Price(0)
    PricePoints = OrderedDict(
        [
            (TechnologyUnit(0), Price(4_000)),
            (TechnologyUnit(10), Price(12_000)),
            (TechnologyUnit(50), Price(16_000)),
            (TechnologyUnit(100), Price(25_000)),
            (TechnologyUnit(200), Price(30_000)),
            (TechnologyUnit(400), Price(40_000)),
            (TechnologyUnit(800), Price(60_000)),
            (TechnologyUnit(1_500), Price(70_000)),
            (TechnologyUnit(5_000), Price(80_000)),
            (TechnologyUnit(10_000), Price(90_000)),
            (TechnologyUnit(20_000), Price(100_000)),
            (TechnologyUnit(150_000), Price(120_000)),
        ]
    )
    BillModifier: BillModifierBoosts = "technology_bill_modifier"
    FloorBill = daily_price_rate(Price(10))
    BillPoints = OrderedDict(
        [
            (TechnologyUnit(0), daily_price_rate(Price(0.01))),
            (TechnologyUnit(10), daily_price_rate(Price(0.02))),
            (TechnologyUnit(50), daily_price_rate(Price(0.03))),
            (TechnologyUnit(100), daily_price_rate(Price(0.04))),
            (TechnologyUnit(200), daily_price_rate(Price(0.05))),
            (TechnologyUnit(400), daily_price_rate(Price(0.06))),
            (TechnologyUnit(800), daily_price_rate(Price(0.07))),
            (TechnologyUnit(1_500), daily_price_rate(Price(0.08))),
            (TechnologyUnit(5_000), daily_price_rate(Price(0.09))),
            (TechnologyUnit(10_000), daily_price_rate(Price(0.1))),
            (TechnologyUnit(20_000), daily_price_rate(Price(0.11))),
            (TechnologyUnit(150_000), daily_price_rate(Price(0.12))),
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
