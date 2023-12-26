from __future__ import annotations

import logging
from datetime import datetime, timedelta
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Protocol, Literal

from sqlalchemy.orm import Session

import host.currency
import host.ureg
from host.defaults import defaults
from host.gameplay_settings import GameplaySettings
from host.nation.ministry import Ministry
from host.nation.models import BankModel

if TYPE_CHECKING:
    from host.nation import Nation

SendingResponses = Literal["success", "insufficient_funds"]
DeductResponses = Literal["insufficient_funds"]

REVENUE_PER_HAPPINESS = 3 * 86400


class FundReceiver(Protocol):
    @host.ureg.Registry.wraps(None, [None, host.currency.Currency])
    def receive(self, funds: host.currency.Currency) -> None:
        raise NotImplementedError


class FundSender(Protocol):
    @host.ureg.Registry.wraps(None, [None, host.currency.Currency, None])
    def send(self, funds: host.currency.Currency, target: FundReceiver) -> SendingResponses:
        raise NotImplementedError


class Bank(Ministry, FundReceiver, FundSender):
    __slots__ = "_identifier", "_player", "_session", "_bank"

    def __init__(self, player: Nation, session: Session):
        self._identifier: int = player.identifier
        self._player: Nation = player
        self._session: Session = session

    @cached_property
    def model(self) -> BankModel:
        bank: Optional[BankModel] = self._session.query(BankModel).filter_by(user_id=self._identifier).first()
        if bank is None:
            self._session.add(
                BankModel(
                    user_id=self._identifier,
                    name=defaults.bank.name.format(self._player.name),
                    treasury=GameplaySettings.bank.starter_funds,
                    tax_rate=defaults.bank.tax_rate,
                    last_accessed=datetime.now(),
                )
            )
            self._session.commit()
            bank = self._session.query(BankModel).filter_by(user_id=self._identifier).first()
        assert bank is not None, "Bank should exist"
        return bank

    @property
    def name(self) -> str:
        return self.model.name

    @name.setter
    def name(self, value: str) -> None:
        self.model.name = value
        self._session.commit()

    @property
    @host.ureg.Registry.wraps(host.currency.Currency, None)
    def funds(self) -> host.currency.Currency:
        self._update_treasury()
        return host.currency.lnd(self.model.treasury)

    @property
    @host.ureg.Registry.wraps(host.currency.CurrencyRate, None)
    def national_revenue(self) -> host.currency.CurrencyRate:
        income_modifier = 1 + self._player.boost.income_modifier

        return self._player.revenue * income_modifier

    @property
    @host.ureg.Registry.wraps(host.currency.CurrencyRate, None)
    def national_bill(self) -> host.currency.CurrencyRate:
        bill_modifier = self._player.boost.bill_modifier
        bill_reduction = self._player.boost.bill_reduction * host.currency.CurrencyRate

        costs = sum(ministry.bill for ministry in self._player.ministries)
        costs = 0 * host.currency.CurrencyRate if costs < bill_reduction else costs - bill_reduction

        return costs * (1 - bill_modifier / 100)

    @property
    @host.ureg.Registry.wraps(host.currency.CurrencyRate, None)
    def national_profit(self) -> host.currency.CurrencyRate:
        revenue: host.currency.CurrencyRate = self.national_revenue
        expenditure: host.currency.CurrencyRate = self.national_bill
        return revenue - expenditure

    @property
    def tax_rate(self) -> float:
        return self.model.tax_rate / 100

    @tax_rate.setter
    def tax_rate(self, value: float) -> None:
        if value > defaults["max_tax_rate"]:
            raise ValueError(f"Tax rate cannot be more than {GameplaySettings.bank.maximum_tax_rate}")
        self.model.tax_rate = value
        self._session.commit()

    @property
    def last_accessed(self) -> datetime:
        return self.model.last_accessed

    def _update_treasury(self) -> None:
        current_time = datetime.now()
        self.model.treasury += int(self._retrieve_profit(current_time).magnitude)
        self.model.last_accessed = current_time
        self._session.commit()

    @host.ureg.Registry.wraps(host.currency.Currency, [None, None])
    def _retrieve_revenue(self, timestamp: datetime) -> host.currency.Currency:
        time_difference: timedelta = timestamp - self.model.last_accessed
        seconds = time_difference.total_seconds() * host.ureg.Registry.seconds
        return self.national_revenue.to(host.currency.Currency / host.ureg.Registry.seconds) * seconds

    @host.ureg.Registry.wraps(host.currency.Currency, [None, None])
    def _retrieve_bill(self, timestamp: datetime) -> host.currency.Currency:
        time_difference: timedelta = timestamp - self.model.last_accessed
        seconds = time_difference.total_seconds() * host.ureg.Registry.seconds
        return self.national_bill.to(host.currency.Currency / host.ureg.Registry.seconds) * seconds

    @host.ureg.Registry.wraps(host.currency.Currency, [None, None])
    def _retrieve_profit(self, timestamp: datetime) -> host.currency.Currency:
        revenue: host.currency.Currency = self._retrieve_revenue(timestamp)
        expenses: host.currency.Currency = self._retrieve_bill(timestamp)
        return revenue - expenses

    @host.ureg.Registry.check(None, host.currency.Currency)
    def add(self, amount: host.currency.Currency) -> None:
        if amount < host.currency.lnd(0):
            raise ValueError("Cannot add negative funds")
        logging.debug(f"Adding {amount} to {self._player.name}'s treasury, Previous: {self.funds}")
        new_funds: host.currency.Currency = self.funds + amount
        self.model.treasury = int(new_funds.magnitude)
        self._session.add(self.model)
        self._session.commit()

    @host.ureg.Registry.check(None, host.currency.Currency)
    def enough_funds(self, amount: host.currency.Currency) -> bool:
        return self.funds >= amount

    @host.ureg.Registry.check(None, host.currency.Currency, None)
    def deduct(self, amount: host.currency.Currency, force: bool = True) -> None:
        if self.funds < amount and not force:
            raise ValueError("Insufficient funds")
        new_funds: host.currency.Currency = self.funds - amount
        self.model.treasury = int(new_funds.magnitude)
        self._session.add(self.model)
        self._session.commit()

    @host.ureg.Registry.wraps(None, [None, host.currency.Currency, None])
    def send(self, amount: host.currency.Currency, target: FundReceiver) -> SendingResponses:
        if self.funds < amount:
            return "insufficient_funds"
        self.deduct(amount)
        try:
            target.receive(amount)
        except Exception as e:
            self.add(amount)
            raise e
        return "success"

    @host.ureg.Registry.wraps(None, [None, host.currency.Currency])
    def receive(self, funds: host.currency.Currency) -> None:
        self.add(funds)
