from typing import NewType, Literal

AllianceId = NewType("AllianceId", int)

AllianceRoles = Literal["Leader", "Officer", "Member"]
