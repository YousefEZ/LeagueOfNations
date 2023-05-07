from typing import NewType, Literal

AllianceId = NewType("AllianceId", str)

AllianceRoles = Literal["Leader", "Officer", "Member"]
