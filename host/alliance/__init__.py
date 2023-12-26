from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host.alliance import types


class Alliance:
    def __init__(self, identifier: types.AllianceId, session: Session):
        self._identifier: types.AllianceId = identifier
        self._session: Session = session
