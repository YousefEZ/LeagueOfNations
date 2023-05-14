from datetime import datetime
from typing import Any, Dict

from sqlalchemy.types import JSON
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, MappedAsDataclass


class Base(MappedAsDataclass, DeclarativeBase):
    type_annotation_map = {
        Dict[str, Any]: JSON
    }


class NotificationModel(Base):
    __tablename__ = "Notifications"

    notification_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str]
    date: Mapped[datetime]
    message: Mapped[str]
    data: Mapped[Dict[str, Any]]
