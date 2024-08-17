from __future__ import annotations

import logging
from datetime import datetime
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Protocol, Literal

from sqlalchemy.orm import Session

from host.currency import Currency, CurrencyRate, daily_currency_rate, as_currency
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
    def receive(self, funds: Currency) -> None:
        raise NotImplementedError


class FundSender(Protocol):
    def send(self, funds: Currency, target: FundReceiver) -> SendingResponses:
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
    @as_currency
    def funds(self) -> float:
        self._update_treasury()
        return self.model.treasury

    @property
    def national_revenue(self) -> CurrencyRate:
        income_modifier = 1 + self._player.boost.income_modifier

        return self._player.revenue * income_modifier

    @property
    def national_bill(self) -> CurrencyRate:
        bill_modifier = self._player.boost.bill_modifier
        bill_reduction = daily_currency_rate(Currency(self._player.boost.bill_reduction))

        costs: CurrencyRate = sum(
            (ministry.bill for ministry in self._player.ministries), start=daily_currency_rate(Currency(0))
        )
        costs = daily_currency_rate(Currency(0)) if costs < bill_reduction else costs - bill_reduction

        return costs * (1 - bill_modifier / 100)

    @property
    def national_profit(self) -> CurrencyRate:
        revenue: CurrencyRate = self.national_revenue
        expenditure: CurrencyRate = self.national_bill
        return revenue - expenditure

    @property
    def tax_rate(self) -> float:
        return self.model.tax_rate / 100

    @tax_rate.setter
    def tax_rate(self, value: float) -> None:
        if value > defaults.bank.tax_rate:
            raise ValueError(f"Tax rate cannot be more than {GameplaySettings.bank.maximum_tax_rate}")
        self.model.tax_rate = value
        self._session.commit()

    @property
    def last_accessed(self) -> datetime:
        return self.model.last_accessed

    def _update_treasury(self) -> None:
        current_time = datetime.now()
        self.model.treasury += int(self._retrieve_profit(current_time))
        self.model.last_accessed = current_time
        self._session.commit()

    def _retrieve_revenue(self, timestamp: datetime) -> Currency:
        return self.national_revenue.amount_in_delta(timestamp - self.model.last_accessed)

    def _retrieve_bill(self, timestamp: datetime) -> Currency:
        return self.national_bill.amount_in_delta(timestamp - self.model.last_accessed)

    def _retrieve_profit(self, timestamp: datetime) -> Currency:
        revenue: Currency = self._retrieve_revenue(timestamp)
        expenses: Currency = self._retrieve_bill(timestamp)
        return revenue - expenses

    def add(self, amount: Currency) -> None:
        if amount < Currency(0):
            raise ValueError("Cannot add negative funds")
        logging.debug(f"Adding {amount} to {self._player.name}'s treasury, Previous: {self.funds}")
        new_funds: Currency = self.funds + amount
        self.model.treasury = int(new_funds)
        self._session.add(self.model)
        self._session.commit()

    def enough_funds(self, amount: Currency) -> bool:
        return self.funds >= amount

    def deduct(self, amount: Currency, force: bool = True) -> None:
        if self.funds < amount and not force:
            raise ValueError("Insufficient funds")
        new_funds: Currency = self.funds - amount
        self.model.treasury = int(new_funds)
        self._session.add(self.model)
        self._session.commit()

    def send(self, funds: Currency, target: FundReceiver) -> SendingResponses:
        if self.funds < funds:
            return "insufficient_funds"
        self.deduct(funds)
        try:
            target.receive(funds)
        except Exception as e:
            self.add(funds)
            raise e
        return "success"

    def receive(self, funds: Currency) -> None:
        self.add(funds)
