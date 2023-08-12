import json
from typing import Dict, Any

from pydantic import BaseModel


class Meta(BaseModel):
    flag: str


class Government(BaseModel):
    type: str


class Bank(BaseModel):
    tax_rate: float


class DefaultsModel(BaseModel):
    flag: Meta
    government: Government
    tax_rate: Bank


with open("settings/defaults.json", "r") as defaults_file:
    defaults: DefaultsModel = DefaultsModel.model_validate(json.load(defaults_file))
