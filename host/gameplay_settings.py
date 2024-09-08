import json

from pydantic import BaseModel


class ForeignGameplaySettings(BaseModel):
    maximum_aid_slots: int
    maximum_aid_amount: float
    aid_slot_expire_days: float


class BankGameplaySettings(BaseModel):
    maximum_tax_rate: float
    starter_funds: int


class InteriorGameplaySettings(BaseModel):
    population_per_infrastructure: int
    revenue_per_population: float
    cashback_modifier: float
    starter_infrastructure: int
    starter_land: float
    starter_technology: int


class TradeGameplaySettings(BaseModel):
    maximum_active_agreements: int
    resources_per_nation: int


class GameplaySettingsModel(BaseModel):
    bank: BankGameplaySettings
    interior: InteriorGameplaySettings
    foreign: ForeignGameplaySettings
    trade: TradeGameplaySettings


with open("settings/gameplay_settings.json", "r") as gameplay_settings_file:
    GameplaySettings: GameplaySettingsModel = GameplaySettingsModel.model_validate(
        json.load(gameplay_settings_file)
    )
