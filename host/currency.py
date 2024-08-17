from __future__ import annotations


from abc import ABC, abstractmethod
from babel import numbers
from collections.abc import Callable
from datetime import timedelta
from dataclasses import dataclass
from functools import wraps
from typing import Any, Generic, Optional, ParamSpec, Protocol, Self, Type, TypeVar, cast

SECONDS_AS_DAY: float = timedelta(days=1).total_seconds()
DAY = timedelta(days=1)


K = TypeVar("K", covariant=True)


class ExpectedType(Protocol[K]):

    def __init__(self, amount: K): ...


T = TypeVar("T", bound=ExpectedType, covariant=True)
P = ParamSpec("P")


@dataclass(slots=True, eq=True, order=True)
class CurrencyABC(ABC):
    _amount: float | int

    @abstractmethod
    def __init__(self, _: float | int): ...

    @property
    @abstractmethod
    def amount(self) -> float | int: ...

    def __iadd__(self, amount: Self) -> Self:
        self._amount += amount.amount
        return self

    def __imul__(self, multiplier: float) -> Self:
        self._amount *= multiplier
        return self

    def __ifloordiv__(self, divisor: float) -> Self:
        self._amount //= divisor
        return self

    def __itruediv__(self, divisor: float) -> Self:
        self._amount /= divisor
        return self

    def __add__(self, amount: Self) -> Self:
        return type(self)(self._amount + amount.amount)

    def __floordiv__(self, divisor: float) -> Self:
        return type(self)(self._amount / divisor)

    def __truediv__(self, divisor: float) -> Self:
        return self / divisor

    def __mul__(self, multiplier: float) -> Self:
        return type(self)(self.amount * multiplier)

    def __int__(self) -> int:
        return int(self.amount)

    def __float__(self) -> float:
        return float(self.amount)

    def __str__(self) -> str:
        return numbers.format_compact_currency(
            self.amount, currency="USD", locale="en_US", fraction_digits=3
        )

    def __repr__(self) -> str:
        return str(self)


C = TypeVar("C", bound=CurrencyABC, covariant=True)


@dataclass(slots=True, eq=True, order=True)
class Currency(CurrencyABC):
    _amount: float | int

    def __init__(self, amount: float | int):
        self._amount = amount

    @property
    def amount(self) -> float | int:
        return self._amount

    def __isub__(self, amount: Price) -> Self:
        self._amount -= amount.amount
        return self

    def __sub__(self, amount: Price) -> Self:
        return type(self)(self._amount - amount.amount)

    def as_rate(self, delta: timedelta) -> CurrencyRate:
        return CurrencyRate(type(self)(self.amount), delta)


class PositiveValue:

    def __init__(self, amount: int | float):
        assert amount > 0.0
        self._amount = amount

    def __get__(self, _, objtype=None) -> int | float:
        return self._amount

    def __set__(self, _, value) -> None:
        assert value >= 0.0
        self._amount = value


class Discount(CurrencyABC):
    def __init__(self, amount: int | float):
        assert amount >= 0.0
        self._amount = amount

    @property
    def amount(self) -> int | float:
        return self._amount


class Price(CurrencyABC):

    def __init__(self, amount: int | float):
        self._amount: int | float = cast(int | float, PositiveValue(amount))

    @property
    def amount(self) -> int | float:
        return self._amount

    def __isub__(self, amount: Discount) -> Self:
        self._amount -= amount.amount
        return self

    def __sub__(self, amount: Discount) -> Self:
        return type(self)(self._amount - amount.amount)

    def as_rate(self, delta: timedelta) -> PriceRate:
        return PriceRate(type(self)(self._amount), delta)


@dataclass(slots=True)
class CurrencyRateABC(ABC, Generic[C]):
    _amount: C
    _time: timedelta

    def __init__(self, amount: C, time: timedelta):
        self._amount = amount
        self._time = time

    def __radd__(self, amount: Any) -> Self:
        return self + amount

    def __iadd__(self, amount: Self) -> Self:
        self._amount += amount.amount_in_delta(self._time)
        return self

    def __imul__(self, multiplier: float) -> Self:
        self._amount *= multiplier
        return self

    def __ifloordiv__(self, divisor: float) -> Self:
        self._amount //= divisor
        return self

    def __itruediv__(self, divisor: float) -> Self:
        self._amount /= divisor
        return self

    def __add__(self, amount: Self) -> Self:
        return type(self)(self._amount + amount.amount_in_delta(self._time), self._time)

    def __mul__(self, multiplier: float) -> Self:
        return type(self)(self._amount * multiplier, self._time)

    def __floordiv__(self, divisor: float) -> Self:
        return type(self)(self._amount / divisor, self._time)

    def __truediv__(self, divisor: float) -> Self:
        return self / divisor

    def per_day(self) -> Self:
        if self._time.total_seconds() == SECONDS_AS_DAY:
            return self

        return type(self)(self.amount_in_delta(DAY), DAY)

    def amount_in_delta(self, delta: timedelta) -> C:
        return type(self._amount)(
            int(self._amount * (delta.total_seconds() / self._time.total_seconds()))
        )

    def __gt__(self, other: Self) -> bool:
        return self.amount_in_delta(DAY) > other.amount_in_delta(DAY)

    def __ge__(self, other: Self) -> bool:
        return self.amount_in_delta(DAY) >= other.amount_in_delta(DAY)

    def __lt__(self, other: Self) -> bool:
        return self.amount_in_delta(DAY) < other.amount_in_delta(DAY)

    def __le__(self, other: Self) -> bool:
        return self.amount_in_delta(DAY) <= other.amount_in_delta(DAY)

    def __eq__(self, other: Self | object) -> bool:
        return isinstance(other, type(self)) and self.amount_in_delta(DAY) == other.amount_in_delta(
            DAY
        )


class CurrencyRate(CurrencyRateABC[Currency]):
    def __isub__(self, amount: PriceRate) -> Self:
        self._amount -= amount.amount_in_delta(self._time)
        return self

    def __sub__(self, amount: PriceRate) -> Self:
        return type(self)(self._amount - amount.amount_in_delta(self._time), self._time)


def daily_currency_rate(amount: Currency | CurrencyRate) -> CurrencyRate:
    assert isinstance(amount, (Currency, CurrencyRate))
    if isinstance(amount, Currency):
        return CurrencyRate(amount, DAY)
    return CurrencyRate(amount.amount_in_delta(DAY), DAY)


DiscountRate = CurrencyRateABC[Discount]


class PriceRate(CurrencyRateABC[Price]):
    def __isub__(self, amount: DiscountRate) -> Self:
        self._amount -= amount.amount_in_delta(self._time)
        return self

    def __sub__(self, amount: DiscountRate) -> Self:
        return type(self)(self._amount - amount.amount_in_delta(self._time), self._time)


def as_currency(func: Callable[P, int | float]) -> Callable[P, Currency]:
    @wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> Currency:
        return Currency(func(*args, **kwargs))

    return decorator


def as_price(func: Callable[P, int | float]) -> Callable[P, Price]:
    @wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> Price:
        return Price(func(*args, **kwargs))

    return decorator


def as_discount(func: Callable[P, int | float]) -> Callable[P, Discount]:
    @wraps(func)
    def decorator(*args: P.args, **kwargs: P.kwargs) -> Discount:
        return Discount(func(*args, **kwargs))

    return decorator


def as_currency_rate(
    delta: timedelta,
) -> Callable[[Callable[P, Currency]], Callable[P, CurrencyRate]]:
    def decorator(func: Callable[P, Currency]) -> Callable[P, CurrencyRate]:
        @wraps(func)
        def new_func(*args: P.args, **kwargs: P.kwargs) -> CurrencyRate:
            return CurrencyRate(func(*args, **kwargs), delta)

        return new_func

    return decorator


def as_price_rate(delta: timedelta) -> Callable[[Callable[P, Price]], Callable[P, PriceRate]]:
    def decorator(func: Callable[P, Price]) -> Callable[P, PriceRate]:
        @wraps(func)
        def new_func(*args: P.args, **kwargs: P.kwargs) -> PriceRate:
            return PriceRate(func(*args, **kwargs), delta)

        return new_func

    return decorator


def as_discount_rate(
    delta: timedelta,
) -> Callable[[Callable[P, Discount]], Callable[P, DiscountRate]]:
    def decorator(func: Callable[P, Discount]) -> Callable[P, DiscountRate]:
        @wraps(func)
        def new_func(*args: P.args, **kwargs: P.kwargs) -> DiscountRate:
            return DiscountRate(func(*args, **kwargs), delta)

        return new_func

    return decorator


def as_daily_currency_rate(func: Callable[P, Currency]) -> Callable[P, CurrencyRate]:
    return wraps(func)(as_currency_rate(DAY)(func))


def as_daily_price_rate(func: Callable[P, Price]) -> Callable[P, PriceRate]:
    return wraps(func)(as_price_rate(DAY)(func))


def as_daily_discount_rate(func: Callable[P, Discount]) -> Callable[P, DiscountRate]:
    return wraps(func)(as_discount_rate(DAY)(func))


def check(*args: Optional[Type]) -> Callable[[Callable[P, T]], Callable[P, T]]:
    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
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
