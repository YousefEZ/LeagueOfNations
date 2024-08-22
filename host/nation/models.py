from __future__ import annotations

from datetime import datetime

from host.base_models import Base
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column


class TradeRequestModel(Base):
    __tablename__ = "TradeRequests"

    trade_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    expires: Mapped[datetime]
    sponsor: Mapped[int]
    recipient: Mapped[int]


class TradeModel(Base):
    __tablename__ = "Trades"

    trade_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    sponsor: Mapped[int]
    recipient: Mapped[int]


class AidRequestModel(Base):
    __tablename__ = "AidRequests"

    aid_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    expires: Mapped[datetime]
    sponsor: Mapped[int]
    recipient: Mapped[int]
    amount: Mapped[int]
    reason: Mapped[str] = mapped_column(String(250))


class AidModel(Base):
    __tablename__ = "Aid"

    aid_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    accepted: Mapped[datetime]
    sponsor: Mapped[int]
    recipient: Mapped[int]
    amount: Mapped[int]
    reason: Mapped[str] = mapped_column(String(250))


class ResourcesModel(Base):
    __tablename__ = "Resources"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    primary: Mapped[str]
    secondary: Mapped[str]


class MetadataModel(Base):
    __tablename__ = "Metadata"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    nation: Mapped[str] = mapped_column(primary_key=True)
    flag: Mapped[str]
    emoji: Mapped[str]
    created: Mapped[datetime]


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
    land: Mapped[float]
    technology: Mapped[int]
    spent_technology: Mapped[int]


class GovernmentModel(Base):
    __tablename__ = "Government"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[str]


class ImprovementModel(Base):
    __tablename__ = "Improvements"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    amount: Mapped[int]
