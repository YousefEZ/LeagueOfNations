from __future__ import annotations

import logging
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from sched import scheduler
from typing import Any, Callable, List, Optional
from uuid import uuid4

from host.base_models import NotificationModel
from host.base_types import UserId
from sqlalchemy import Engine
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class Notification:
    user_id: UserId
    message: str


@dataclass(frozen=True)
class ScheduledNotification(Notification):
    time: datetime
    data: Optional[dict[str, Any]] = None
    notification_id: str = field(default_factory=lambda: str(hex(int(uuid4()))))


class NotifierError(Exception):
    pass


class Notifier:
    """Singleton class that handles the tracking and consumption of Notifications"""

    _instance: Optional[Notifier] = None
    _scheduler: scheduler = scheduler()
    _hooks: List[Callable[[ScheduledNotification], Any]] = []
    _loaded: bool = False
    _lock: threading.Lock = threading.Lock()
    _condition: threading.Condition = threading.Condition()

    def __init__(self, engine: Engine):
        self._engine = engine
        if not self._loaded:
            self._load_notifications_from_db()

    def _load_notifications_from_db(self) -> None:
        with self._lock:
            if self._loaded:
                return
            with Session(self._engine) as session:
                result = session.query(
                    NotificationModel.notification_id, NotificationModel.date
                ).all()
                for notification in result:
                    self._schedule(notification.notification_id, notification.date)
                self._loaded = True

    def _schedule(self, notification_id: str, date: datetime) -> None:
        """Private method that schedules a notification for consumption by the view"""
        now = datetime.now()
        logging.info(f"Scheduling For {date - now} from now")
        if date < now:
            self._display(notification_id)
            return
        delay = int((date - now).total_seconds())
        with self._condition:
            self._scheduler.enter(delay, 0, self._display, argument=(notification_id,))
            self._condition.notify()

    def _display(self, notification_id: str) -> None:
        logging.info(f"Displaying notification: {notification_id}")
        with Session(self._engine) as session:
            result = (
                session.query(NotificationModel).filter_by(notification_id=notification_id).first()
            )
            assert result is not None, "ScheduledNotification not found"
            notification = ScheduledNotification(
                user_id=UserId(result.user_id),
                time=result.date,
                message=result.message,
                data=result.data,
                notification_id=result.notification_id,
            )

            for hook in self._hooks:
                hook(notification)

            session.delete(result)
            session.commit()

    def _add_notification_to_db(self, notification: ScheduledNotification) -> None:
        """Private method that stores the notification in the database"""
        with Session(self._engine) as session:
            session.add(
                NotificationModel(
                    notification_id=notification.notification_id,
                    user_id=int(notification.user_id),
                    date=notification.time,
                    message=notification.message,
                    data=notification.data,
                )
            )
            session.commit()

    @staticmethod
    def hook(hook: Callable[[ScheduledNotification], Any]) -> None:
        """Method that adds a hook to the notifier

        Args:
            hook (Callable[[ScheduledNotification], Coroutine[Any, Any, Any]]): the hook to be added
        """
        Notifier._hooks.append(hook)

    def schedule(self, notification: ScheduledNotification) -> None:
        """Method that schedules a notification for consumption by the view"""
        self._add_notification_to_db(notification)
        self._schedule(notification.notification_id, notification.time)

    def start(self) -> None:
        """This method is start when the view is ready, so it begins consuming updates"""

        def run():
            with self._condition:
                while True:
                    now = time.time()
                    deadline = self._scheduler.run(blocking=False)
                    sleep_time = deadline - now if deadline is not None else None
                    self._condition.wait(
                        sleep_time if sleep_time is not None and sleep_time > 0 else None
                    )

        threading.Thread(target=run).start()
