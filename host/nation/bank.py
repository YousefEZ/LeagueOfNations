from __future__ import annotations

import logging
from datetime import datetime, timedelta
from enum import IntEnum, auto
from functools import cached_property
from typing import TYPE_CHECKING, Optional, Protocol

from host.currency import (
    Currency,
    CurrencyRate,
    Discount,
    Price,
    PriceRate,
    as_currency,
    daily_discount_rate,
    daily_price_rate,
)
from host.defaults import defaults
from host.gameplay_settings import GameplaySettings
from host.nation.ministry import Ministry
from host.nation.models import BankModel
from sqlalchemy.orm import Session

if TYPE_CHECKING:
    from host.nation import Nation


class SendingResponses(IntEnum):
    SUCCESS = auto()
    INSUFFICIENT_FUNDS = auto()


class DeductResponses(IntEnum):
    SUCCESS = auto()
    INSUFFICIENT_FUNDS = auto()


class TaxResponses(IntEnum):
    SUCCESS = auto()
    INVALID_RATE = auto()


class NameResponses(IntEnum):
    SUCCESS = auto()


REVENUE_PER_HAPPINESS: CurrencyRate = CurrencyRate(Currency(3), timedelta(seconds=1))


class FundReceiver(Protocol):
    def receive(self, funds: Currency) -> None:
        raise NotImplementedError


class FundSender(Protocol):
    def send(self, amount: Price, target: FundReceiver) -> SendingResponses:
        raise NotImplementedError


class Bank(Ministry, FundReceiver, FundSender):
    __slots__ = "_identifier", "_player", "_session", "_bank"

    def __init__(self, player: Nation, session: Session):
        self._identifier: int = player.identifier
        self._player: Nation = player
        self._session: Session = session

    @cached_property
    def model(self) -> BankModel:
        bank: Optional[BankModel] = (
            self._session.query(BankModel).filter_by(user_id=self._identifier).first()
        )
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

    def set_name(self, value: str) -> NameResponses:
        self.model.name = value
        self._session.commit()
        return NameResponses.SUCCESS

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
    def national_bill(self) -> PriceRate:
        bill_modifier = self._player.boost.bill_modifier
        bill_reduction = daily_discount_rate(Discount(self._player.boost.bill_reduction))

        costs: PriceRate = (
            sum(
                (ministry.bill for ministry in self._player.ministries),
                start=daily_price_rate(Price(0)),
            )
            - bill_reduction
        )

        return costs * (1 - bill_modifier / 100)

    @property
    def national_profit(self) -> CurrencyRate:
        revenue: CurrencyRate = self.national_revenue
        expenditure: PriceRate = self.national_bill
        return revenue - expenditure

    @property
    def tax_rate(self) -> float:
        return self.model.tax_rate / 100

    def set_tax_rate(self, value: float) -> TaxResponses:
        if value > defaults.bank.tax_rate:
            return TaxResponses.INVALID_RATE
        self.model.tax_rate = value
        self._session.commit()
        return TaxResponses.SUCCESS

    @property
    def last_accessed(self) -> datetime:
        return self.model.last_accessed

    def _update_treasury(self) -> None:
        current_time = datetime.now()
        delta = current_time - self.model.last_accessed
        if delta <= timedelta():
            return
        self.model.treasury += int(self._retrieve_profit(delta))
        self.model.last_accessed = current_time
        self._session.commit()

    def _retrieve_revenue(self, delta: timedelta) -> Currency:
        return self.national_revenue.amount_in_delta(delta)

    def _retrieve_bill(self, delta: timedelta) -> Price:
        return self.national_bill.amount_in_delta(delta)

    def _retrieve_profit(self, delta: timedelta) -> Currency:
        revenue: Currency = self._retrieve_revenue(delta)
        expenses: Price = self._retrieve_bill(delta)
        return revenue - expenses

    def add(self, amount: Currency) -> None:
        if amount < Currency(0):
            raise ValueError("Cannot add negative funds")
        logging.debug(f"Adding {amount} to {self._player.name}'s treasury, Previous: {self.funds}")
        new_funds: Currency = self.funds + amount
        self.model.treasury = int(new_funds)
        self._session.add(self.model)
        self._session.commit()

    def can_purchase(self, amount: Price) -> bool:
        return self.funds.can_afford(amount)

    def enough_funds(self, amount: Currency) -> bool:
        return self.funds >= amount

    def deduct(self, price: Price, force: bool = True) -> None:
        if not self.can_purchase(price) and not force:
            raise ValueError("Insufficient funds")
        new_funds: Currency = self.funds - price
        self.model.treasury = int(new_funds)
        self._session.add(self.model)
        self._session.commit()

    def send(self, amount: Price, target: FundReceiver) -> SendingResponses:
        if not self.can_purchase(amount):
            return SendingResponses.INSUFFICIENT_FUNDS
        self.deduct(amount)
        try:
            target.receive(Currency(amount.amount))
        except Exception as e:
            self.add(Currency(amount.amount))
            raise e
        return SendingResponses.SUCCESS

    def receive(self, funds: Currency) -> None:
        self.add(funds)
