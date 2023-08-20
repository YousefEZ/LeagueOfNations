import json
from functools import cached_property
from typing import TYPE_CHECKING

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host.nation import models, types
from host.nation.ministry import Ministry

if TYPE_CHECKING:
    from host.nation import Nation


class Government(Ministry):

    def __init__(self, player: Nation, session: Session):
        self._player = player
        self._session = session

    @cached_property
    def model(self) -> models.GovernmentModel:
        government = self._session.query(models.GovernmentModel).filter_by(user_id=self._player.identifier).first()

        if government is None:
            government = models.GovernmentModel(user_id=self._player.identifier, government="monarchy")
            self._session.add(government)
            self._session.commit()

        return government

    @property
    def government(self) -> types.government.Government:
        return Governments[self.model.type]

    @government.setter
    def government(self, government_type: types.government.GovernmentTypes) -> None:
        self.model.type = government_type
        self._session.commit()

    def boost(self) -> types.boosts.BoostsLookup:
        return self.government.boosts
