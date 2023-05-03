import json
from functools import cached_property
from typing import TYPE_CHECKING, Dict

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import models, types

from host.ministry import Ministry

if TYPE_CHECKING:
    from host.nation import Nation

with open("object/governments.json", "r") as governments_file:
    Governments: Dict[types.GovernmentTypes, types.Government] = json.load(governments_file)


class Government(Ministry):

    def __init__(self, player: Nation, engine: Engine):
        self._player = player
        self._engine = engine

    @cached_property
    def model(self) -> models.GovernmentModel:
        with Session(self._engine) as session:
            government = session.query(models.GovernmentModel).filter_by(user_id=self._player.identifier).first()

            if government is None:
                government = models.GovernmentModel(user_id=self._player.identifier, government="monarchy")
                session.add(government)
                session.commit()

        return government

    @property
    def government(self) -> types.Government:
        return Governments[self.model.government]

    @government.setter
    def government(self, government: types.GovernmentTypes) -> None:
        with Session(self._engine) as session:
            self.model.government = government
            session.commit()

    def boost(self, boost: types.Boosts) -> float:
        return self.government["boosts"].get(boost, 0.0)
