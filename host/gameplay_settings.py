import json

from pydantic import BaseModel


class BankGameplaySettings(BaseModel):
    maximum_tax_rate: float
    starter_funds: float


class InteriorGameplaySettings(BaseModel):
    population_per_infrastructure: int
    revenue_per_population: float
    cashback_modifier: float
    starter_infrastructure: float
    starter_land: float
    starter_technology: float


class GameplaySettingsModel(BaseModel):
    bank: BankGameplaySettings
    interior: InteriorGameplaySettings


with open("settings/gameplay_settings.json", "r") as gameplay_settings_file:
    GameplaySettings: GameplaySettingsModel = GameplaySettingsModel.model_validate(json.load(gameplay_settings_file))
