from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from sched import scheduler
from typing import Optional, Callable, Any, List
from uuid import uuid4

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from host.base_models import NotificationModel
from host.base_types import UserId

__all__ = "Notification", "NotifierError", "add_listener", "schedule", "start"

NOTIFIER_RESOLUTION: timedelta = timedelta(seconds=5)


@dataclass(frozen=True)
class Notification:
    user_id: UserId
    message: str
    data: Optional[dict[str, Any]] = None
    time: datetime = field(default_factory=datetime.now)
    notification_id: str = field(default_factory=lambda: str(hex(int(uuid4()))))


class NotifierError(Exception):
    pass


_scheduler: scheduler = scheduler()
_listeners: List[Callable[[Notification], Any]] = []
_lock: threading.Lock = threading.Lock()
_thread: Optional[threading.Thread] = None
_running: bool = False


def add_listener(listener: Callable[[Notification], None]) -> None:
    """Method that adds a hook to the notifier

    Args:
        listener (Callable[[Notification], Coroutine[Any, Any, Any]]): the hook to be added
    """
    _listeners.append(listener)


def schedule(notification: Notification, engine: Engine) -> None:
    """Method that schedules a notification for consumption by the view

    Args:
        notification (Notification): the notification to be scheduled
        engine (Engine): the database engine
    """
    now = datetime.now()
    if notification.time < now:
        for listener in _listeners:
            listener(notification)
        return
    _add_notification_to_db(notification, engine)
    delay = int((notification.time - now).total_seconds())
    _scheduler.enter(delay, 0, _display, argument=(notification.notification_id,))


def start(engine: Engine) -> None:
    """Runs the Notifier

    Args:
        engine (Engine): the database engine to load the notifications from the database from
    """
    global _thread, _running
    if _thread is not None:
        raise NotifierError("Notifier already running")
    _load_notifications_from_db(engine)

    def run():
        while True:
            _scheduler.run(blocking=False)
            time.sleep(NOTIFIER_RESOLUTION.total_seconds())
            with _lock:
                if not _running:
                    break

    _running = True
    _thread = threading.Thread(target=run, daemon=True).start()


def stop() -> None:
    """Stops the Notifier"""
    global _running

    if _thread is None or not _thread.is_alive():
        return
    with _lock:
        _running = False
    _thread.join()


def _load_notifications_from_db(engine: Engine) -> None:
    with Session(engine) as session:
        result = session.query(NotificationModel.notification_id, NotificationModel.date).all()
        for notification in result:
            _schedule_from_db(notification.notification_id, notification.date, engine)


def _schedule_from_db(notification_id: str, date: datetime, engine: Engine) -> bool:
    """Private method that schedules a notification for consumption by the view"""
    now = datetime.now()
    if date < now:
        _display(notification_id, engine)
        return False
    delay = int((date - now).total_seconds())
    _scheduler.enter(delay, 0, _display, argument=(notification_id,))
    return True


def _display(notification_id: str, engine: Engine) -> None:
    with Session(engine) as session:
        result = session.query(NotificationModel).filter_by(notification_id=notification_id).first()
        assert result is not None, "Notification not found"
        notification = Notification(
            user_id=result.user_id,
            message=result.message,
            data=result.data,
            time=result.date,
            notification_id=result.notification_id
        )
        for listener in _listeners:
            listener(notification)

        session.delete(result)
        session.commit()


def _add_notification_to_db(notification: Notification, engine: Engine) -> None:
    """Private method that stores the notification in the database"""
    with Session(engine) as session:
        session.add(NotificationModel(
            notification_id=notification.notification_id,
            user_id=notification.user_id,
            date=notification.time,
            message=notification.message,
            keywords=notification.data
        ))
        session.commit()
