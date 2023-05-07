from __future__ import annotations

import asyncio
import warnings
from dataclasses import dataclass, field
from datetime import datetime
from sched import scheduler
from typing import Optional, Callable, Any, List, Coroutine, Dict, Union
from uuid import uuid4

import discord.ui
from qalib import Renderer
from qalib.template_engines.jinja2 import Jinja2
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host.base_models import NotificationModel
from host.base_types import UserId


@dataclass(frozen=True)
class BaseNotification:
    user_id: UserId
    time: datetime


@dataclass(frozen=True)
class TemplateNotification(BaseNotification):
    template: str
    key: str
    keywords: Dict[str, Any]
    notification_id: str = field(default_factory=lambda: str(hex(int(uuid4()))))


@dataclass(frozen=True)
class Notification(BaseNotification):
    payload: Optional[str] = None
    notification_id: str = field(default_factory=lambda: str(hex(int(uuid4()))))


class NotifierError(Exception):
    pass


def _template_notification(notification: TemplateNotification) -> Notification:
    renderer: Renderer[str] = Renderer(Jinja2(), notification.template)
    message = renderer.render(notification.key, keywords=notification.keywords)
    assert not isinstance(message, discord.ui.Modal)
    return Notification(
        user_id=notification.user_id,
        time=notification.time,
        payload=message.content,
        notification_id=notification.notification_id
    )


class Notifier:
    _instance: Optional[Notifier] = None

    def __init__(self, engine: Engine):
        self._engine = engine
        self._scheduler = scheduler()
        self._scheduler.run(blocking=False)
        self._notification_hooks: List[Callable[[str], Coroutine[Any, Any, Any]]] = []

    def _load_notification_from_db(self):
        with Session(self._engine) as session:
            result = session.query(NotificationModel).all()
            for row in result:
                notification = Notification(
                    user_id=row.user_id,
                    time=row.date,
                    payload=row.message,
                    notification_id=row.notification_id
                )
                self._scheduler.enterabs((notification.time - datetime.now()).seconds, 0, self.display,
                                         argument=(notification,))

    def __new__(cls, *args, **kwargs):
        if not hasattr(cls, '_instance'):
            cls._instance = Notifier(*args, **kwargs)
            return cls._instance
        warnings.warn("An instance has already been instantiated use get_instance instead", RuntimeWarning)

    @staticmethod
    def get_instance() -> Notifier:
        if Notifier._instance is None:
            raise NotifierError("Notifier has not been started")
        return Notifier._instance

    def _delete_notification(self, notification_id: str) -> None:
        with Session(self._engine) as session:
            session.query(NotificationModel).filter_by(notification_id=notification_id).delete()
            session.commit()

    async def _display(self, notification: Notification):
        if notification.payload is None:
            self._delete_notification(notification.notification_id)
            return

        for hook in self._notification_hooks:
            await hook(notification.payload)

        self._delete_notification(notification.notification_id)

    def display(self, notification: Notification):
        asyncio.get_running_loop().create_task(self._display(notification))

    def _add_notification_to_db(self, notification: Notification):
        with Session(self._engine) as session:
            session.add(NotificationModel(
                notification_id=notification.notification_id,
                user_id=notification.user_id,
                date=notification.time,
                message=notification.payload
            ))
            session.commit()

    def schedule(self, notification: Union[Notification, TemplateNotification]):
        delay = (notification.time - datetime.now()).seconds

        if isinstance(notification, TemplateNotification):
            notification = _template_notification(notification)

        assert notification.payload is not None, "Message content cannot be None"
        self._add_notification_to_db(notification)
        self._scheduler.enter(delay, 0, self.display, argument=(notification,))
