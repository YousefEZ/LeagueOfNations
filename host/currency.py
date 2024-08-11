from __future__ import annotations


from collections.abc import Callable
from babel import numbers
from datetime import timedelta
from dataclasses import dataclass
from typing import Any, Optional, ParamSpec, Protocol, Type, TypeVar

SECONDS_AS_DAY: float = timedelta(days=1).total_seconds()
DAY = timedelta(days=1)


K = TypeVar("K", covariant=True)


class ExpectedType(Protocol[K]):

    def __init__(self, amount: K): ...


T = TypeVar("T", bound=ExpectedType, covariant=True)
P = ParamSpec("P")


@dataclass(slots=True)
class CurrencyRate:
    _amount: Currency
    _time: timedelta

    def __init__(self, amount: Currency, time: timedelta):
        self._amount = amount
        self._time = time

    def __radd__(self, amount: Any) -> CurrencyRate:
        return self + amount

    def __iadd__(self, amount: CurrencyRate) -> CurrencyRate:
        self._amount += amount.amount_in_delta(self._time)
        return self

    def __isub__(self, amount: CurrencyRate) -> CurrencyRate:
        self._amount -= amount.amount_in_delta(self._time)
        return self

    def __imul__(self, multiplier: float) -> CurrencyRate:
        self._amount *= multiplier
        return self

    def __ifloordiv__(self, divisor: float) -> CurrencyRate:
        self._amount //= divisor
        return self

    def __itruediv__(self, divisor: float) -> CurrencyRate:
        self._amount /= divisor
        return self

    def __add__(self, amount: CurrencyRate) -> CurrencyRate:
        return CurrencyRate(self._amount + amount.amount_in_delta(self._time), self._time)

    def __sub__(self, amount: CurrencyRate) -> CurrencyRate:
        return CurrencyRate(self._amount - amount.amount_in_delta(self._time), self._time)

    def __mul__(self, multiplier: float) -> CurrencyRate:
        return CurrencyRate(self._amount * multiplier, self._time)

    def __floordiv__(self, divisor: float) -> CurrencyRate:
        return CurrencyRate(self._amount / divisor, self._time)

    def __truediv__(self, divisor: float) -> CurrencyRate:
        return self / divisor

    def per_day(self) -> CurrencyRate:
        if self._time.total_seconds() == SECONDS_AS_DAY:
            return self

        return CurrencyRate(self.amount_in_delta(DAY), DAY)

    def amount_in_delta(self, delta: timedelta) -> Currency:
        return Currency(int(self._amount * (delta.total_seconds() / self._time.total_seconds())))

    def __gt__(self, other: CurrencyRate) -> bool:
        return self.amount_in_delta(DAY) > other.amount_in_delta(DAY)

    def __ge__(self, other: CurrencyRate) -> bool:
        return self.amount_in_delta(DAY) >= other.amount_in_delta(DAY)

    def __lt__(self, other: CurrencyRate) -> bool:
        return self.amount_in_delta(DAY) < other.amount_in_delta(DAY)

    def __le__(self, other: CurrencyRate) -> bool:
        return self.amount_in_delta(DAY) <= other.amount_in_delta(DAY)

    def __eq__(self, other: CurrencyRate | object) -> bool:
        return isinstance(other, CurrencyRate) and self.amount_in_delta(DAY) == other.amount_in_delta(DAY)


class DailyCurrencyRate(CurrencyRate):

    def __init__(self, amount: Currency | CurrencyRate):
        assert isinstance(amount, (Currency, CurrencyRate))
        if isinstance(amount, Currency):
            super().__init__(amount, DAY)
        else:
            super().__init__(amount.amount_in_delta(DAY), DAY)


@dataclass(slots=True, eq=True, order=True)
class Currency:
    _amount: float | int

    def __init__(self, amount: float | int):
        self._amount = amount

    @property
    def amount(self) -> float | int:
        return self._amount

    def __iadd__(self, amount: Currency) -> Currency:
        self._amount += amount.amount
        return self

    def __isub__(self, amount: Currency) -> Currency:
        self._amount -= amount.amount
        return self

    def __imul__(self, multiplier: float) -> Currency:
        self._amount *= multiplier
        return self

    def __ifloordiv__(self, divisor: float) -> Currency:
        self._amount //= divisor
        return self

    def __itruediv__(self, divisor: float) -> Currency:
        self._amount /= divisor
        return self

    def __add__(self, amount: Currency) -> Currency:
        return Currency(self._amount + amount.amount)

    def __sub__(self, amount: Currency) -> Currency:
        return Currency(self._amount - amount.amount)

    def __floordiv__(self, divisor: float) -> Currency:
        return Currency(self.amount / divisor)

    def __truediv__(self, divisor: float) -> Currency:
        return self / divisor

    def __mul__(self, multiplier: float) -> Currency:
        return Currency(int(self.amount * multiplier))

    def as_rate(self, delta: timedelta) -> CurrencyRate:
        return CurrencyRate(Currency(self.amount), delta)

    def __int__(self) -> int:
        return int(self.amount)

    def __float__(self) -> float:
        return float(self.amount)

    def __str__(self) -> str:
        return numbers.format_compact_currency(self.amount, currency="USD", locale="en_US", fraction_digits=3)

    def __repr__(self) -> str:
        return str(self)


def as_currency_rate(delta: timedelta) -> Callable[[Callable[P, Currency]], Callable[P, CurrencyRate]]:
    def decorator(func: Callable[P, Currency]) -> Callable[P, CurrencyRate]:
        def new_func(*args: P.args, **kwargs: P.kwargs) -> CurrencyRate:
            return CurrencyRate(func(*args, **kwargs), delta)

        return new_func

    return decorator


def as_daily_currency_rate(func: Callable[P, Currency]) -> Callable[P, CurrencyRate]:
    return as_currency_rate(DAY)(func)


def as_currency(func: Callable[P, int | float]) -> Callable[P, Currency]:
    def decorator(*args: P.args, **kwargs: P.kwargs) -> Currency:
        return Currency(func(*args, **kwargs))

    return decorator


def check(*args: Optional[Type]) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        def new_func(*p_args: P.args, **p_kwargs: P.kwargs) -> T:
            for p_arg, n_arg in zip(p_args, args):
                assert n_arg is None or isinstance(p_arg, n_arg)
            return func(*p_args, **p_kwargs)

        return new_func

    return decorator


def lnd(value: int | float) -> Currency:
    return Currency(value)


def lnd_rate(value: int | float, delta: timedelta = timedelta(days=1)) -> CurrencyRate:
    return CurrencyRate(Currency(value), delta)
