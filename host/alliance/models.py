from datetime import datetime

from sqlalchemy.orm import mapped_column, Mapped

from host import base_types
from host.alliance import types
from host.base_models import Base


class AllianceMetaModel(Base):
    __tablename__ = "AllianceMeta"

    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str]
    flag: Mapped[str]
    date_founded: Mapped[datetime]
    description: Mapped[str]


class AllianceBankModel(Base):
    __tablename__ = "AllianceBank"

    id: Mapped[str] = mapped_column(primary_key=True)
    bank_name: Mapped[str] = mapped_column(primary_key=True)
    treasury: Mapped[int]


class AllianceMemberModel(Base):
    __tablename__ = "AllianceMember"

    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(primary_key=True)
    role: Mapped[types.AllianceRoles]
    date_joined: Mapped[datetime]
