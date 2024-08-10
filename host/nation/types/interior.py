from __future__ import annotations

from collections import OrderedDict
from typing import Protocol, Optional, TypeVar

from host import currency
from host.nation import models
from host.nation.types.basic import InfrastructureUnit, LandUnit, TechnologyUnit
from host.nation.types.boosts import PriceModifierBoosts, BillModifierBoosts

K = TypeVar("K")


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

    @staticmethod
    def singleton() -> Data[K]:
        raise NotImplementedError


class InfrastructurePoints(Data[InfrastructureUnit]):
    _singleton: Optional[InfrastructurePoints] = None
    PriceModifier: PriceModifierBoosts = "infrastructure_cost_modifier"
    FloorPrice = currency.lnd(500)
    PricePoints = OrderedDict(
        [
            (InfrastructureUnit(20), currency.lnd(12)),
            (InfrastructureUnit(100), currency.lnd(15)),
            (InfrastructureUnit(200), currency.lnd(20)),
            (InfrastructureUnit(1_000), currency.lnd(25)),
            (InfrastructureUnit(3_000), currency.lnd(30)),
            (InfrastructureUnit(4_000), currency.lnd(40)),
            (InfrastructureUnit(5_000), currency.lnd(60)),
            (InfrastructureUnit(8_000), currency.lnd(70)),
            (InfrastructureUnit(15_000), currency.lnd(80)),
        ]
    )
    BillModifier: BillModifierBoosts = "infrastructure_bill_modifier"
    FloorBill = currency.lnd_rate(20)
    BillPoints = OrderedDict(
        [
            (InfrastructureUnit(100), currency.lnd_rate(0.04)),
            (InfrastructureUnit(200), currency.lnd_rate(0.05)),
            (InfrastructureUnit(300), currency.lnd_rate(0.06)),
            (InfrastructureUnit(500), currency.lnd_rate(0.07)),
            (InfrastructureUnit(700), currency.lnd_rate(0.08)),
            (InfrastructureUnit(1_000), currency.lnd_rate(0.09)),
            (InfrastructureUnit(2_000), currency.lnd_rate(0.11)),
            (InfrastructureUnit(3_000), currency.lnd_rate(0.13)),
            (InfrastructureUnit(4_000), currency.lnd_rate(0.15)),
            (InfrastructureUnit(5_000), currency.lnd_rate(0.17)),
            (InfrastructureUnit(8_000), currency.lnd_rate(0.1725)),
            (InfrastructureUnit(32_000), currency.lnd_rate(0.175)),
            (InfrastructureUnit(35_000), currency.lnd_rate(0.15)),
            (InfrastructureUnit(37_000), currency.lnd_rate(0.14)),
            (InfrastructureUnit(40_000), currency.lnd_rate(0.13)),
        ]
    )

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
    FloorPrice: currency.Currency = currency.lnd(400)
    PricePoints: OrderedDict[LandUnit, currency.Currency] = OrderedDict(
        [
            (LandUnit(20), currency.lnd(1.5)),
            (LandUnit(30), currency.lnd(2)),
            (LandUnit(40), currency.lnd(2.5)),
            (LandUnit(100), currency.lnd(3)),
            (LandUnit(150), currency.lnd(3.5)),
            (LandUnit(200), currency.lnd(5)),
            (LandUnit(250), currency.lnd(10)),
            (LandUnit(300), currency.lnd(15)),
            (LandUnit(400), currency.lnd(20)),
            (LandUnit(500), currency.lnd(25)),
            (LandUnit(800), currency.lnd(30)),
            (LandUnit(1_200), currency.lnd(35)),
            (LandUnit(2_000), currency.lnd(40)),
            (LandUnit(3_000), currency.lnd(45)),
            (LandUnit(4_000), currency.lnd(55)),
            (LandUnit(8_000), currency.lnd(75)),
        ]
    )
    BillModifier: BillModifierBoosts = "land_bill_modifier"
    FloorBill: currency.CurrencyRate = currency.lnd_rate(0.3)
    BillPoints: OrderedDict[LandUnit, currency.CurrencyRate] = OrderedDict(
        [
            (LandUnit(20), currency.lnd_rate(0.001)),
            (LandUnit(30), currency.lnd_rate(0.002)),
            (LandUnit(40), currency.lnd_rate(0.003)),
            (LandUnit(100), currency.lnd_rate(0.004)),
            (LandUnit(150), currency.lnd_rate(0.005)),
            (LandUnit(200), currency.lnd_rate(0.006)),
            (LandUnit(250), currency.lnd_rate(0.007)),
            (LandUnit(300), currency.lnd_rate(0.008)),
            (LandUnit(400), currency.lnd_rate(0.009)),
            (LandUnit(500), currency.lnd_rate(0.01)),
            (LandUnit(800), currency.lnd_rate(0.011)),
            (LandUnit(1_200), currency.lnd_rate(0.012)),
            (LandUnit(2_000), currency.lnd_rate(0.013)),
            (LandUnit(3_000), currency.lnd_rate(0.014)),
            (LandUnit(4_000), currency.lnd_rate(0.015)),
            (LandUnit(8_000), currency.lnd_rate(0.016)),
        ]
    )

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
    FloorPrice = currency.lnd(0)
    PricePoints = OrderedDict(
        [
            (TechnologyUnit(0), currency.lnd(4_000)),
            (TechnologyUnit(10), currency.lnd(12_000)),
            (TechnologyUnit(50), currency.lnd(16_000)),
            (TechnologyUnit(100), currency.lnd(25_000)),
            (TechnologyUnit(200), currency.lnd(30_000)),
            (TechnologyUnit(400), currency.lnd(40_000)),
            (TechnologyUnit(800), currency.lnd(60_000)),
            (TechnologyUnit(1_500), currency.lnd(70_000)),
            (TechnologyUnit(5_000), currency.lnd(80_000)),
            (TechnologyUnit(10_000), currency.lnd(90_000)),
            (TechnologyUnit(20_000), currency.lnd(100_000)),
            (TechnologyUnit(150_000), currency.lnd(120_000)),
        ]
    )
    BillModifier: BillModifierBoosts = "technology_bill_modifier"
    FloorBill = currency.lnd_rate(10)
    BillPoints = OrderedDict(
        [
            (TechnologyUnit(0), currency.lnd_rate(0.01)),
            (TechnologyUnit(10), currency.lnd_rate(0.02)),
            (TechnologyUnit(50), currency.lnd_rate(0.03)),
            (TechnologyUnit(100), currency.lnd_rate(0.04)),
            (TechnologyUnit(200), currency.lnd_rate(0.05)),
            (TechnologyUnit(400), currency.lnd_rate(0.06)),
            (TechnologyUnit(800), currency.lnd_rate(0.07)),
            (TechnologyUnit(1_500), currency.lnd_rate(0.08)),
            (TechnologyUnit(5_000), currency.lnd_rate(0.09)),
            (TechnologyUnit(10_000), currency.lnd_rate(0.1)),
            (TechnologyUnit(20_000), currency.lnd_rate(0.11)),
            (TechnologyUnit(150_000), currency.lnd_rate(0.12)),
        ]
    )

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
