from __future__ import annotations

import json
from typing import Dict, List, NewType

from host.nation.types.boosts import BoostsLookup
from pydantic import BaseModel


ResourceName = NewType("ResourceName", str)


class Resource(BaseModel, frozen=True):
    emoji: str
    description: str
    boosts: BoostsLookup


with open("objects/resources.json", "r", encoding="utf8") as resources_file:
    Resources: Dict[str, Resource] = {
        identifier: Resource.model_validate(resource)
        for identifier, resource in json.load(resources_file).items()
    }

RESOURCE_NAMES: List[ResourceName] = list(map(ResourceName, Resources.keys()))
