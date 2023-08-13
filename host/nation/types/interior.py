from collections import OrderedDict
from enum import Enum, auto
from typing import Protocol, TypeVar, TYPE_CHECKING

from host import currency
from host.nation import models
from host.nation.types.basic import InfrastructureUnit, LandUnit, TechnologyUnit, land
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


class InfrastructurePoints(Data[InfrastructureUnit]):
    PriceModifier: PriceModifierBoosts = "infrastructure_cost_modifier"
    FloorPrice = currency.lnd(500)
    PricePoints = OrderedDict([
        (InfrastructureUnit(20), currency.lnd(12)),
        (InfrastructureUnit(100), currency.lnd(15)),
        (InfrastructureUnit(200), currency.lnd(20)),
        (InfrastructureUnit(1_000), currency.lnd(25)),
        (InfrastructureUnit(3_000), currency.lnd(30)),
        (InfrastructureUnit(4_000), currency.lnd(40)),
        (InfrastructureUnit(5_000), currency.lnd(60)),
        (InfrastructureUnit(8_000), currency.lnd(70)),
        (InfrastructureUnit(15_000), currency.lnd(80)),
    ])
    BillModifier: BillModifierBoosts = "infrastructure_bill_modifier"
    FloorBill = currency.lnd_rate(20)
    BillPoints = OrderedDict([
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
    ])

    @staticmethod
    def get(interior: models.InteriorModel) -> InfrastructureUnit:
        return interior.infrastructure

    @staticmethod
    def set(interior: models.InteriorModel, value: InfrastructureUnit) -> None:
        interior.infrastructure = value


class LandPoints(Data[LandUnit]):
    PriceModifier: PriceModifierBoosts = "land_cost_modifier"
    FloorPrice: currency.Currency = currency.lnd(400)
    PricePoints: OrderedDict[LandUnit, currency.Currency] = OrderedDict([
        (land(20), currency.lnd(1.5)),
        (land(30), currency.lnd(2)),
        (land(40), currency.lnd(2.5)),
        (land(100), currency.lnd(3)),
        (land(150), currency.lnd(3.5)),
        (land(200), currency.lnd(5)),
        (land(250), currency.lnd(10)),
        (land(300), currency.lnd(15)),
        (land(400), currency.lnd(20)),
        (land(500), currency.lnd(25)),
        (land(800), currency.lnd(30)),
        (land(1_200), currency.lnd(35)),
        (land(2_000), currency.lnd(40)),
        (land(3_000), currency.lnd(45)),
        (land(4_000), currency.lnd(55)),
        (land(8_000), currency.lnd(75))
    ])
    BillModifier: BillModifierBoosts = "land_bill_modifier"
    FloorBill: currency.Currency = currency.lnd_rate(0.3)
    BillPoints: OrderedDict[LandUnit, currency.CurrencyRate] = OrderedDict([
        (land(20), currency.lnd_rate(0.001)),
        (land(30), currency.lnd_rate(0.002)),
        (land(40), currency.lnd_rate(0.003)),
        (land(100), currency.lnd_rate(0.004)),
        (land(150), currency.lnd_rate(0.005)),
        (land(200), currency.lnd_rate(0.006)),
        (land(250), currency.lnd_rate(0.007)),
        (land(300), currency.lnd_rate(0.008)),
        (land(400), currency.lnd_rate(0.009)),
        (land(500), currency.lnd_rate(0.01)),
        (land(800), currency.lnd_rate(0.011)),
        (land(1_200), currency.lnd_rate(0.012)),
        (land(2_000), currency.lnd_rate(0.013)),
        (land(3_000), currency.lnd_rate(0.014)),
        (land(4_000), currency.lnd_rate(0.015)),
        (land(8_000), currency.lnd_rate(0.016))
    ])

    @staticmethod
    def get(interior: models.InteriorModel) -> LandUnit:
        return interior.land

    @staticmethod
    def set(interior: models.InteriorModel, value: LandUnit) -> None:
        interior.land = value


class TechnologyPoints(Data[TechnologyUnit]):
    PriceModifier: PriceModifierBoosts = "technology_cost_modifier"
    FloorPrice = currency.lnd(0)
    PricePoints = OrderedDict([
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
        (TechnologyUnit(150_000), currency.lnd(120_000))
    ])
    BillModifier: BillModifierBoosts = "technology_bill_modifier"
    FloorBill = currency.lnd_rate(10)
    BillPoints = OrderedDict([
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
        (TechnologyUnit(150_000), currency.lnd_rate(0.12))
    ])

    @staticmethod
    def get(interior: models.InteriorModel) -> TechnologyUnit:
        return interior.technology

    @staticmethod
    def set(interior: models.InteriorModel, value: TechnologyUnit) -> None:
        interior.technology = value


class PurchaseResult(Enum):
    SUCCESS = auto()
    INSUFFICIENT_FUNDS = auto()
    NEGATIVE_AMOUNT = auto()


class SellResult(Enum):
    SUCCESS = auto()
    NEGATIVE_AMOUNT = auto()
    INSUFFICIENT_AMOUNT = auto()
