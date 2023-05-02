from typing import TYPE_CHECKING, List

from sqlalchemy import Engine

from host.ministry import Ministry

if TYPE_CHECKING:
    from host.nation import Nation


class AidRequest:
    pass


class Foreign(Ministry):

    def __init__(self, player: Nation, engine: Engine):
        self._player = player
        self._engine = engine

    @property
    def sent(self) -> List[AidRequest]:
        return []
