from __future__ import annotations

import json
from datetime import timedelta
from typing import Dict, cast, Literal, TypedDict

from typing_extensions import NotRequired

from . import basic
from host import currency

HousingTypes = Literal[
    "house", "small apartment-complex", "medium apartment-complex", "large apartment-complex",
    "extra-large apartment-complex"
]
CommercialInstitutions = Literal["Market", "Shopping Mall", "Office Park", "Industrial Park"]
EducationalInstitutions = Literal["School", "University"]
MedicalInstitutions = Literal["Hospital", "Clinic"]
EmployableBuildings = Literal[CommercialInstitutions, EducationalInstitutions, MedicalInstitutions]
BuildingTypes = Literal[HousingTypes, CommercialInstitutions, EducationalInstitutions, MedicalInstitutions]


class BuildTime(TypedDict):
    weeks: NotRequired[int]
    days: NotRequired[int]
    hours: NotRequired[int]
    minutes: NotRequired[int]
    seconds: NotRequired[int]


class BuildingDescription(TypedDict):
    description: str
    emoji: str
    land: float
    price: float
    bill: float
    build_time: BuildTime


class HousingDescription(BuildingDescription):
    name: HousingTypes
    population: int


class EmployableDescription(BuildingDescription):
    employment: int


class CommercialDescription(EmployableDescription):
    name: CommercialInstitutions
    income: float


class MedicalDescription(EmployableDescription):
    name: MedicalInstitutions
    health: float


class EducationalDescription(EmployableDescription):
    name: EducationalInstitutions
    literacy: float


with open("objects/infrastructure.json", "r", encoding="utf8") as file:
    INFRASTRUCTURE: Dict[str, BuildingDescription] = json.load(file)


class Building:

    def __init__(self, name: BuildingTypes, amount: int):
        self._name = name
        self._amount = amount

    @property
    def building(self) -> BuildingDescription:
        return INFRASTRUCTURE[self._name]

    @property
    def name(self) -> str:
        return self._name

    @property
    def amount(self) -> int:
        return self._amount

    @property
    @currency.ureg.wraps(currency.CurrencyRate, None)
    def bill(self) -> currency.CurrencyRate:
        return self.building["bill"] * self._amount * currency.CurrencyRate

    @property
    def build_time(self) -> timedelta:
        return timedelta(**self.building["build_time"])

    @property
    @currency.ureg.wraps(currency.Currency, None)
    def price(self) -> currency.Currency:
        return INFRASTRUCTURE[self._name]["price"] * self._amount * currency.Currency

    @property
    def emoji(self) -> str:
        return self.building["emoji"]

    @property
    def description(self) -> str:
        return self.building["description"]


class Housing(Building):

    def __init__(self, name: HousingTypes, amount: int):
        super().__init__(name, amount)

    @property
    def building(self) -> HousingDescription:
        return cast(HousingDescription, INFRASTRUCTURE[self._name])

    @property
    def population(self) -> basic.Population:
        return basic.Population(self.building["population"] * self._amount)


class EmployableBuilding(Building):

    def __init__(self, name: EmployableBuildings, amount: int):
        super().__init__(name, amount)

    @property
    def building(self) -> EmployableDescription:
        return cast(EmployableDescription, INFRASTRUCTURE[self._name])

    @property
    def employment(self) -> basic.Employment:
        return basic.Employment(self.building["employment"] * self._amount)


class Education(EmployableBuilding):

    def __init__(self, name: EducationalInstitutions, amount: int):
        super().__init__(name, amount)

    @property
    def building(self) -> EducationalDescription:
        return cast(EducationalDescription, INFRASTRUCTURE[self._name])

    @property
    def literacy(self) -> basic.Literacy:
        return basic.Literacy(self.building["literacy"] * self._amount)


class Health(EmployableBuilding):

    def __init__(self, name: MedicalInstitutions, amount: int):
        super().__init__(name, amount)

    @property
    def building(self) -> MedicalDescription:
        return cast(MedicalDescription, INFRASTRUCTURE[self._name])

    @property
    def health(self) -> basic.Health:
        return basic.Health(self.building["health"] * self._amount)


class Commerce(EmployableBuilding):

    def __init__(self, name: CommercialInstitutions, amount: int):
        super().__init__(name, amount)

    @property
    def building(self) -> CommercialDescription:
        return cast(CommercialDescription, INFRASTRUCTURE[self._name])

    @property
    @currency.ureg.wraps(currency.CurrencyRate, None)
    def income(self) -> currency.CurrencyRate:
        return self.building["income"] * self._amount * currency.CurrencyRate


INFRASTRUCTURE_GROUPS = {
    "housing": Housing,
    "education": Education,
    "health": Health,
    "commerce": Commerce
}


def get_building(name: BuildingTypes, amount: int) -> Building:
    for group in INFRASTRUCTURE:
        if name in INFRASTRUCTURE[group]:
            return INFRASTRUCTURE_GROUPS[group](name, amount)
    raise ValueError(f"Building {name} not found")
