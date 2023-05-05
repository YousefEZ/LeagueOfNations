from typing import TYPE_CHECKING

from sqlalchemy import Engine

if TYPE_CHECKING:
    from host.alliance import Alliance


class AllianceBank:

    def __init__(self, alliance: Alliance, engine: Engine):
        self._alliance: Alliance = alliance
        self._engine: Engine = engine
