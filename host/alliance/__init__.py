from sqlalchemy import Engine

from host.alliance import types


class Alliance:

    def __init__(self, identifier: types.AllianceId, engine: Engine):
        self._identifier: types.AllianceId = identifier
        self._engine: Engine = engine
