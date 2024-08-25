from datetime import timedelta

import pytest
from unittest.mock import patch, PropertyMock
from freezegun import freeze_time
from hypothesis import assume, given, settings
from hypothesis import strategies as st

from host.defaults import defaults
from host.currency import Currency, Discount, Price, daily_currency_rate
from host.gameplay_settings import GameplaySettings
from host.nation.bank import SendingResponses, TaxResponses
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
        player = UserGenerator.generate_player(session)
        with patch("host.nation.Nation.revenue", new_callable=PropertyMock) as revenue_mock:
            revenue_mock.return_value = daily_currency_rate(Currency(revenue))
            rate, last_accessed = player.bank.national_profit, player.bank.last_accessed
            increase = Currency(int(rate.amount_in_delta(delta)))

            with freeze_time(last_accessed + delta):
                assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) + increase


@given(st.integers(min_value=0, max_value=100_000))
@settings(deadline=None, max_examples=15)
def test_receive(amount):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        player.bank.receive(Currency(amount))
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) + Currency(amount)


@given(st.integers(min_value=0, max_value=GameplaySettings.bank.starter_funds))
@settings(deadline=None, max_examples=15)
def test_send(amount: int):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        target = UserGenerator.generate_player(session)
        assert player.bank.send(Price(amount), target.bank) == SendingResponses.SUCCESS
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds) - Price(amount)
        assert target.bank.funds == Currency(GameplaySettings.bank.starter_funds) + Currency(amount)


@given(st.integers(min_value=GameplaySettings.bank.starter_funds + 1))
@settings(deadline=None, max_examples=15)
def test_empty_send(amount: int):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        target = UserGenerator.generate_player(session)
        assert player.bank.send(Price(amount), target.bank) == SendingResponses.INSUFFICIENT_FUNDS
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds)
        assert target.bank.funds == Currency(GameplaySettings.bank.starter_funds)


@given(st.integers(min_value=0, max_value=GameplaySettings.bank.starter_funds))
@settings(deadline=None, max_examples=15)
def test_exception_on_send(amount: int):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        target = UserGenerator.generate_player(session)
        with patch("host.nation.bank.Bank.receive", side_effect=ValueError), pytest.raises(
            ValueError
        ):
            player.bank.send(Price(amount), target.bank)
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


@given(st.floats(min_value=0, max_value=GameplaySettings.bank.maximum_tax_rate))
def test_valid_tax_rate(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        assert player.bank.set_tax_rate(amount) == TaxResponses.SUCCESS
        assert player.bank.tax_rate == amount / 100


@given(st.floats(max_value=-1))
def test_negative_tax_rate(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        assert player.bank.set_tax_rate(amount) == TaxResponses.INVALID_RATE
        assert player.bank.tax_rate == defaults.bank.tax_rate / 100


@given(st.floats(min_value=GameplaySettings.bank.maximum_tax_rate + 1))
def test_invalid_tax_rate(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        assert player.bank.set_tax_rate(amount) == TaxResponses.INVALID_RATE
        assert player.bank.tax_rate == defaults.bank.tax_rate / 100


@given(st.floats(min_value=1))
def test_add_negative_funds(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        with pytest.raises(ValueError):
            player.bank.receive(Currency(-amount))
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds)


@given(st.floats(min_value=GameplaySettings.bank.starter_funds + 1))
def test_deduct_overdraft(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        with pytest.raises(ValueError):
            player.bank.deduct(Price(amount), force=False)
        assert player.bank.funds == Currency(GameplaySettings.bank.starter_funds)


@given(st.floats(min_value=0, max_value=GameplaySettings.bank.starter_funds))
def test_enough_funds_true(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        assert player.bank.enough_funds(Currency(amount))


@given(st.floats(min_value=GameplaySettings.bank.starter_funds + 1))
def test_enough_funds_false(amount: float):
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        assert not player.bank.enough_funds(Currency(amount))


@given(st.lists(st.characters()))
def test_name_change(name: list[str]):
    string = "".join(name)
    assume(string.isprintable())
    with TestingSessionLocal() as session:
        player = UserGenerator.generate_player(session)
        player.bank.set_name(string)
        assert player.bank.name == string
