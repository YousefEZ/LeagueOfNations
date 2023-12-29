from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING

import qalib
from qalib.template_engines.jinja2 import Jinja2

import host.notifier
from host.notifier import Notifier

if TYPE_CHECKING:
    from lon import LeagueOfNations


class NotificationRenderer:
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot
        self.notifier = Notifier(self.bot.engine)
        self.notifier.hook(self.display_notification)
        self._renderer = qalib.Renderer(Jinja2(), "templates/notifications.xml")

    def display_notification(self, notification: host.notifier.Notification) -> None:
        print("displaying notification")
        self.bot.loop.create_task(self.render(notification))

    async def render(self, notification: host.notifier.Notification) -> None:
        user = await self.bot.fetch_user(notification.user_id)
        await user.send("This is a notification")

    def start(self) -> None:
        self.notifier.start()
