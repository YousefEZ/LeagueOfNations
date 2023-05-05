from datetime import datetime

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from host.base_types import UserId


class Base(DeclarativeBase):
    pass


class NotificationModel(Base):
    __tablename__ = "Notifications"

    notification_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[UserId]
    date: Mapped[datetime]
    message: Mapped[str]
