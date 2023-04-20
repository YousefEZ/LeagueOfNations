from datetime import datetime
from typing import TYPE_CHECKING, Optional

import pint
import sqlalchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, Session

if TYPE_CHECKING:
    from host.nation import Nation


class Base(DeclarativeBase):
    pass


class BankModel(Base):
    __tablename__ = "Bank"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column()
    treasury: Mapped[int] = mapped_column()
    tax_rate: Mapped[int] = mapped_column()
    last_accessed: Mapped[datetime] = mapped_column()


class Bank:
    __slots__ = "_identifier", "_player", "_engine", "_bank"

    def __init__(self, identifier: int, player: Nation, engine: sqlalchemy.Engine):
        self._identifier: int = identifier
        self._player: Nation = player
        self._engine: sqlalchemy.Engine = engine
        with Session(self._engine) as session:
            bank: Optional[BankModel] = session.query(BankModel).filter_by(user_id=self._identifier).first()
            assert bank is not None, f"Bank does not exist for {self._identifier}"
            self._bank: BankModel = bank

    @property
    def funds(self) -> int:
        treasury = self._bank.treasury
        with Session(self._engine) as session:
            self._bank.treasury = treasury
            session.commit()
        return treasury

    def _update_treasury(self) -> None:
        with Session(self._engine) as session:
            self._bank.treasury += self._retrieve_revenue(datetime.now()) - self._retrieve_expenses(datetime.now())
            session.commit()

    def _retrieve_revenue(self, timestamp: datetime) -> int:
        time_difference = timestamp - self._bank.last_accessed
        total_revenue = self._player.improvements.revenue * time_difference

    def _retrieve_expenses(self, timestamp: datetime) -> int:
        ...
