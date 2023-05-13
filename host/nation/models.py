from __future__ import annotations

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from host.base_models import Base
from host.nation import types


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


class AidModel(Base):
    __tablename__ = "Aid"

    aid_id: Mapped[str] = mapped_column(primary_key=True)
    date: Mapped[datetime]
    expires: Mapped[datetime]
    sponsor: Mapped[int]
    recipient: Mapped[int]
    amount: Mapped[int]


class ResourcesModel(Base):
    __tablename__ = "Resources"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    primary: Mapped[types.resources.ResourceTypes]
    secondary: Mapped[types.resources.ResourceTypes]


class MetadataModel(Base):
    __tablename__ = "Metadata"

    user_id: Mapped[int] = mapped_column(primary_key=True)
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
    technology: Mapped[int]
    spent_technology: Mapped[int]


class InfrastructureModel(Base):
    __tablename__ = "Infrastructure"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    building: Mapped[types.interior.BuildingTypes]
    amount: Mapped[int]


class BuildRequestModel(Base):
    __tablename__ = "BuildRequests"

    build_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    building: Mapped[types.interior.BuildingTypes]
    amount: Mapped[int]
    start: Mapped[datetime]


class GovernmentModel(Base):
    __tablename__ = "Government"

    user_id: Mapped[int] = mapped_column(primary_key=True)
    type: Mapped[types.government.GovernmentTypes]
