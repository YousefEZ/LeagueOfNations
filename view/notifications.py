from __future__ import annotations

import logging
from typing import TYPE_CHECKING

import qalib
from qalib.template_engines.jinja2 import Jinja2

import host.notifier
from host.notifier import Notifier, ScheduledNotification

if TYPE_CHECKING:
    from lon import LeagueOfNations


class NotificationRenderer:
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot
        self.notifier = Notifier(self.bot.engine)
        self.notifier.hook(self.display_notification)
        self._renderer = qalib.Renderer(Jinja2(), "templates/notifications.xml")

    def display_notification(self, notification: ScheduledNotification) -> None:
        logging.debug("[NOTIFICATION][DISPLAY] NotificationId=%s", notification.notification_id)
        self.bot.loop.create_task(self.render(notification))

    async def render(self, notification: host.notifier.Notification) -> None:
        logging.debug("[NOTIFICATION][SENDING] UserId=%s", notification.user_id)
        try:
            user = await self.bot.fetch_user(notification.user_id)
            await user.send(
                **self._renderer.render(
                    "notification", keywords={"notification": notification}
                ).dict()
            )
        except Exception as e:
            logging.error("[NOTIFICATION][ERROR] UserId=%s, Error=%s", notification.user_id, e)
        else:
            logging.debug("[NOTIFICATION][SENT] UserId=%s", notification.user_id)

    def start(self) -> None:
        self.notifier.start()
