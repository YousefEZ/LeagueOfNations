from __future__ import annotations

from datetime import datetime, timedelta
from typing import TYPE_CHECKING, Optional, Protocol, Literal

from pint import Quantity
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host import types
from host.ministry import Ministry
from host.models import BankModel

if TYPE_CHECKING:
    from host.nation import Nation

SendingResponses = Literal["success", "insufficient_funds"]
DeductResponses = Literal["insufficient_funds"]

REVENUE_PER_HAPPINESS = 3 * 86400


class FundReceiver(Protocol):

    def receive(self, funds: Quantity) -> None:
        raise NotImplementedError


class FundSender(Protocol):

    def send(self, funds: Quantity, target: FundReceiver) -> SendingResponses:
        raise NotImplementedError


class Bank(Ministry, FundReceiver, FundSender):
    __slots__ = "_identifier", "_player", "_engine", "_bank"

    def __init__(self, player: Nation, engine: Engine):
        self._identifier: int = player.identifier
        self._player: Nation = player
        self._engine: Engine = engine
        with Session(self._engine) as session:
            bank: Optional[BankModel] = session.query(BankModel).filter_by(user_id=self._identifier).first()
            assert bank is not None, f"Bank does not exist for {self._identifier}"
            self._bank: BankModel = bank

    @property
    @types.ureg.wraps(types.Currency, None)
    def funds(self) -> Quantity:
        self._update_treasury()
        return self._bank.treasury

    @property
    @types.ureg.wraps(types.CurrencyRate, None)
    def national_revenue(self) -> Quantity:
        income_modifier = self._player.boost("income_modifier")
        income_increase = self._player.boost("income_increase") * types.CurrencyRate

        revenue = self._player.revenue
        revenue += sum(ministry.revenue for ministry in self._player.ministries) * types.CurrencyRate + income_increase
        return revenue * (1 + income_modifier / 100)

    @types.ureg.wraps(types.CurrencyRate, None)
    def national_bill(self) -> Quantity:
        bill_modifier = self._player.boost("bill_modifier")
        bill_reduction = self._player.boost("bill_reduction") * types.CurrencyRate

        costs = sum(ministry.bill for ministry in self._player.ministries)
        costs = 0 * types.CurrencyRate if costs < bill_reduction else costs - bill_reduction

        return costs * (1 - bill_modifier / 100)

    @property
    @types.ureg.wraps(types.CurrencyRate, None)
    def national_profit(self) -> Quantity:
        revenue: Quantity = self.national_revenue
        expenditure: Quantity = self.national_bill
        return revenue - expenditure

    @property
    def tax_rate(self) -> float:
        return self._bank.tax_rate

    @tax_rate.setter
    def tax_rate(self, value: float) -> None:
        self._bank.tax_rate = value
        with Session(self._engine) as session:
            session.commit()

    @property
    def last_accessed(self) -> datetime:
        return self._bank.last_accessed

    def _update_treasury(self) -> None:
        current_time = datetime.now()
        self._bank.treasury += int(self._retrieve_profit(current_time).magnitude)
        self._bank.last_accessed = current_time
        with Session(self._engine) as session:
            session.commit()

    @types.ureg.wraps(types.Currency, None)
    def _retrieve_revenue(self, timestamp: datetime) -> Quantity:
        time_difference: timedelta = timestamp - self._bank.last_accessed
        seconds = time_difference.total_seconds() * types.ureg.seconds
        return self.national_revenue.to(types.Currency / types.ureg.seconds) * seconds

    @types.ureg.wraps(types.Currency, None)
    def _retrieve_bill(self, timestamp: datetime) -> Quantity:
        time_difference: timedelta = timestamp - self._bank.last_accessed
        seconds = time_difference.total_seconds() * types.ureg.seconds
        return self.national_bill.to(types.Currency / types.ureg.seconds) * seconds

    @types.ureg.wraps(types.Currency, None)
    def _retrieve_profit(self, timestamp: datetime) -> Quantity:
        revenue: Quantity = self._retrieve_revenue(timestamp)
        expenses: Quantity = self._retrieve_bill(timestamp)
        return revenue - expenses

    @types.ureg.wraps(None, [None, types.Currency])
    def add(self, amount: Quantity) -> None:
        if amount < 0 * types.Currency:
            raise ValueError("Cannot add negative funds")
        self._bank.treasury = self.funds + amount
        with Session(self._engine) as session:
            session.commit()

    @types.ureg.wraps(None, [None, types.Currency])
    def enough_funds(self, amount: Quantity) -> bool:
        return self.funds >= amount

    @types.ureg.wraps(None, [None, types.Currency, None])
    def deduct(self, amount: Quantity, force: bool = True) -> None:
        if self._bank < amount and not force:
            raise ValueError("Insufficient funds")
        new_funds: Quantity = self.funds - amount
        self._bank.treasury = int(new_funds.magnitude)
        with Session(self._engine) as session:
            session.commit()

    @types.ureg.wraps(None, [None, types.Currency, None])
    def send(self, amount: Quantity, target: FundReceiver) -> SendingResponses:
        if self.funds < amount:
            return "insufficient_funds"
        self.deduct(amount)
        try:
            target.receive(amount)
        except Exception as e:
            self.add(amount)
            raise e
        return "success"

    @types.ureg.wraps(None, [None, types.Currency])
    def receive(self, funds: Quantity) -> None:
        self.add(funds)
