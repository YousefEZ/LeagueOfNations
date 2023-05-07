import json
from typing import Dict, Any

with open("defaults.json", "r") as defaults:
    Defaults: Dict[str, Any] = json.load(defaults)
