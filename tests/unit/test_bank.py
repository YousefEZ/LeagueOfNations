from datetime import timedelta
from time import sleep

import pytest
from unittest.mock import patch, PropertyMock
from freezegun import freeze_time
from hypothesis import given, settings
from hypothesis import strategies as st

from host.currency import Currency, Discount, Price, daily_currency_rate
from host.nation import Nation
from host.gameplay_settings import GameplaySettings
from host.nation.bank import SendingResponses
from tests.test_utils import TestingSessionLocal, UserGenerator


def test_starter_funds(player):
    assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds)


@given(
    st.timedeltas(min_value=timedelta(seconds=1), max_value=timedelta(days=1)),
    st.integers(min_value=1, max_value=100_000),
)
@settings(deadline=None, max_examples=15)
def test_revenue_increase_randomized(delta: timedelta, revenue: int):
    with TestingSessionLocal() as session:
        player = Nation.start(UserGenerator.generate_id(), UserGenerator.generate_name(), session)
        with patch("host.nation.Nation.revenue", new_callable=PropertyMock) as revenue_mock:
            revenue_mock.return_value = daily_currency_rate(Currency(revenue))
            rate, last_accessed = player.bank.national_profit, player.bank.model.last_accessed
            increase = Currency(int(rate.amount_in_delta(delta)))

            with freeze_time(last_accessed + delta):
                assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) + increase


def test_revenue_increase(player: Nation):
    rate = player.bank.national_revenue
    increase = rate.amount_in_delta(timedelta(seconds=1))
    sleep(1)
    assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) + increase


@given(st.integers(min_value=0, max_value=100_000))
@settings(deadline=None, max_examples=15)
def test_receive(amount):
    with TestingSessionLocal() as session:
        player = Nation.start(UserGenerator.generate_id(), UserGenerator.generate_name(), session)
        player.bank.receive(Currency(amount))
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) + Currency(amount)


@given(st.integers(min_value=0, max_value=GameplaySettings.bank.starter_funds))
@settings(deadline=None, max_examples=15)
def test_send(amount: int):
    with TestingSessionLocal() as session:
        player = Nation.start(UserGenerator.generate_id(), UserGenerator.generate_name(), session)
        target = Nation.start(UserGenerator.generate_id(), UserGenerator.generate_name(), session)
        assert player.bank.send(Price(amount), target.bank) == SendingResponses.SUCCESS
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) - Price(amount)
        assert target.bank.funds == Currency(GameplaySettings.bank.starter_funds) + Currency(amount)


@given(st.integers(min_value=GameplaySettings.bank.starter_funds + 1))
@settings(deadline=None, max_examples=15)
def test_empty_send(amount: int):
    with TestingSessionLocal() as session:
        player = Nation.start(UserGenerator.generate_id(), UserGenerator.generate_name(), session)
        target = Nation.start(UserGenerator.generate_id(), UserGenerator.generate_name(), session)
        assert player.bank.send(Price(amount), target.bank) == SendingResponses.INSUFFICIENT_FUNDS
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds)
        assert target.bank.funds == Currency(GameplaySettings.bank.starter_funds)


@given(st.integers(max_value=-1))
def test_negative_price(amount: int):
    with pytest.raises(ValueError):
        Price(amount)


@given(st.integers(max_value=-1))
def test_negative_discounts(amount: int):
    with pytest.raises(ValueError):
        Discount(amount)
