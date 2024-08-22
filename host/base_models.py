from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column
from sqlalchemy.types import JSON


class Base(MappedAsDataclass, DeclarativeBase):
    type_annotation_map = {Dict[str, Any]: JSON}


class NotificationModel(Base):
    __tablename__ = "Notifications"

    notification_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[int]
    date: Mapped[datetime]
    message: Mapped[str]
    data: Mapped[Optional[Dict[str, Any]]]
