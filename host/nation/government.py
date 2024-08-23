from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

from host.nation.ministry import Ministry
from host.nation.models import GovernmentModel
from host.nation.types.government import Governments, GovernmentSchema, GovernmentTypes
from host.nation.types.boosts import BoostsLookup


if TYPE_CHECKING:
    from host.nation import Nation


class Government(Ministry):
    __slots__ = "_player", "_session"

    def __init__(self, player: Nation, session: Session):
        self._player: Nation = player
        self._session: Session = session

    def set(self, government: GovernmentTypes) -> None:
        self.model.type = government
        self._session.commit()

    @cached_property
    def model(self) -> GovernmentModel:
        government = (
            self._session.query(GovernmentModel).filter_by(user_id=self._player.identifier).first()
        )

        if government is None:
            government = GovernmentModel(user_id=self._player.identifier, type="monarchy")
            self._session.add(government)
            self._session.commit()

        return government

    @property
    def type(self) -> GovernmentSchema:
        return Governments[self.model.type]

    @type.setter
    def type(self, government_type: GovernmentTypes) -> None:
        self.model.type = government_type
        self._session.commit()

    def boost(self) -> BoostsLookup:
        return self.type.boosts
