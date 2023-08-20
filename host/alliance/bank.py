from typing import TYPE_CHECKING

from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from host.alliance import Alliance


class AllianceBank:

    def __init__(self, alliance: Alliance, session: Session):
        self._alliance: Alliance = alliance
        self._engine: Session = session
