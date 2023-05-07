import json
from functools import cached_property
from typing import TYPE_CHECKING, Dict

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host.nation import models, types
from host.nation.ministry import Ministry

if TYPE_CHECKING:
    from host.nation import Nation

with open("object/governments.json", "r") as governments_file:
    Governments: Dict[
        types.government.GovernmentTypes, types.government.Government] = json.load(governments_file)


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
    def government(self) -> types.government.Government:
        return Governments[self.model.type]

    @government.setter
    def government(self, government_type: types.government.GovernmentTypes) -> None:
        with Session(self._engine) as session:
            self.model.type = government_type
            session.commit()

    def boost(self, boost: types.boosts.Boosts) -> float:
        return self.government["boosts"].get(boost, 0.0)
