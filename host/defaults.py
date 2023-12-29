import json

from pydantic import BaseModel


class Meta(BaseModel):
    flag: str
    emoji: str


class Government(BaseModel):
    type: str


class Bank(BaseModel):
    name: str
    tax_rate: float


class DefaultsModel(BaseModel):
    meta: Meta
    government: Government
    bank: Bank


with open("settings/defaults.json", "r") as defaults_file:
    defaults: DefaultsModel = DefaultsModel.model_validate(json.load(defaults_file))
