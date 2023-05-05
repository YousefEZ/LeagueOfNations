from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from host.base_models import Base
from host.nation import types
from host.nation.types import ResourceTypes


class TradeRequestModel(Base):
    __tablename__ = "TradeRequests"

    trade_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    expires: Mapped[datetime]
    sponsor: Mapped[str]
    recipient: Mapped[str]


class TradeModel(Base):
    __tablename__ = "Trades"

    trade_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    sponsor: Mapped[str]
    recipient: Mapped[str]


class AidRequestModel(Base):
    __tablename__ = "AidRequests"

    aid_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    expires: Mapped[datetime]
    sponsor: Mapped[str]
    recipient: Mapped[str]
    amount: Mapped[int]


class AidModel(Base):
    __tablename__ = "Aid"

    aid_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    expires: Mapped[datetime]
    sponsor: Mapped[str]
    recipient: Mapped[str]
    amount: Mapped[int]


class ResourcesModel(Base):
    __tablename__ = "Resources"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    primary: Mapped[ResourceTypes]
    secondary: Mapped[ResourceTypes]


class MetadataModel(Base):
    __tablename__ = "metadata"

    user_id: Mapped[str] = mapped_column(primary_key=True)
    nation: Mapped[str] = mapped_column(primary_key=True)
    flag: Mapped[str]


class BankModel(Base):
    __tablename__ = "Bank"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    treasury: Mapped[int]
    tax_rate: Mapped[float]
    last_accessed: Mapped[datetime]


class InteriorModel(Base):
    __tablename__ = "Interior"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    infrastructure: Mapped[int]
    land: Mapped[int]


class ImprovementsModel(Base):
    __tablename__ = "Improvements"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[types.ImprovementTypes]
    quantity: Mapped[int]


class GovernmentModel(Base):
    __tablename__ = "Government"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[types.GovernmentTypes]
