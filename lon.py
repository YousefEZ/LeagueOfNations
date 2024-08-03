from __future__ import annotations

import logging
import os
from typing import Optional

import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

import host.base_models
from host.base_types import UserId
from host.nation import Nation
from view.notifications import NotificationRenderer

cogs = "start", "economy", "search", "government", "aid"
connect_to_db = False


class LeagueOfNations(commands.AutoShardedBot):
    def __init__(self, engine: Engine, session: Session):
        super().__init__(
            command_prefix="-",
            owner_id=251351879408287744,
            reconnect=True,
            case_insensitive=True,
            intents=discord.Intents.all(),
        )
        self.engine: Engine = engine
        self.session: Session = session
        host.base_models.Base.metadata.create_all(self.engine)
        self.notification_renderer = NotificationRenderer(self)

    async def setup_hook(self) -> None:
        self.loop.create_task(self.ready())

    def get_nation(self, user_id: int) -> Nation:
        """Get the nation of the user with that user identifier

        Args:
            user_id (UserId): The ID of the user to get

        Returns (discord.User): The user
        """
        return Nation(UserId(user_id), self.session)

    def get_nation_from_name(self, nation_name: str) -> Optional[Nation]:
        return Nation.fetch_from_name(nation_name, self.session)

    async def ready(self):
        await self.wait_until_ready()

        try:
            for cog in cogs:
                await self.load_extension(f"view.cogs.{cog}")
        except Exception as e:
            print("*[CLIENT][LOADING_EXTENSION][STATUS] ERROR ", e)
        else:
            print("*[CLIENT][LOADING_EXTENSION][STATUS] SUCCESS")

        await self.tree.sync()
        self.notification_renderer.start()
        print("*[CLIENT][NOTIFICATIONS][STATUS] READY")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    load_dotenv()

    TOKEN = os.getenv("DISCORD_TOKEN")
    URL = os.getenv("DATABASE_URL")
    assert TOKEN is not None, "MISSING TOKEN IN .env FILE"
    assert URL is not None, "MISSING DATABASE_URL IN .env FILE"

    engine = create_engine(URL, echo=False)
    with Session(engine) as session:
        LeagueOfNations(engine, session).run(token=TOKEN)
