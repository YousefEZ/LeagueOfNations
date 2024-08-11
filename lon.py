from __future__ import annotations

from functools import wraps
import logging
import os
from typing import Awaitable, Callable, Coroutine, Literal, Optional
from typing_extensions import Concatenate, ParamSpec

import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session
from qalib.interaction import QalibInteraction

import host.base_models
from host.base_types import UserId
from host.nation import Nation
from view.notifications import NotificationRenderer

cogs = "start", "economy", "search", "government", "aid"
connect_to_db = False

mechanisms_messages = Literal[
    "nation_lookup", "nation_preview", "lookup_nation_name_not_found", "lookup_nation_id_not_found"
]

P = ParamSpec("P")


def interaction_morph(
    func: Callable[[discord.Interaction], Awaitable[None]]
) -> Callable[[discord.ui.Item, discord.Interaction], Awaitable[None]]:
    @wraps(func)
    async def f(_: discord.ui.Item, interaction: discord.Interaction) -> None:
        await func(interaction)

    return f


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

    async def get_user_from_id_lookup(
        self,
        interaction: QalibInteraction[mechanisms_messages],
        user_id: int,
        func: Callable[Concatenate[Nation, P], Coroutine[None, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        nation = self.get_nation(user_id)
        if not nation.exists:
            await interaction.display("lookup_nation_id_not_found", keywords={"require_mechanisms": True}, view=None)
            return

        async def on_accept(_: discord.ui.Button, i: discord.Interaction):
            await i.response.defer()
            await func(nation, *args, **kwargs)

        async def on_reject(_: discord.ui.Button, i: discord.Interaction):
            await i.response.defer()
            await interaction.response.send_message("Cancelled")

        await interaction.display(
            "nation_preview",
            keywords={"nation": nation, "require_mechanisms": True},
            callables={"on_accept": on_accept, "on_reject": on_reject},
        )

    async def get_user_from_nation_lookup(
        self,
        interaction: QalibInteraction[mechanisms_messages],
        nation_name: str,
        func: Callable[Concatenate[Nation, P], Coroutine[None, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        nations = Nation.search_for_nations(nation_name, self.session)
        if not nations:
            await interaction.display("lookup_nation_name_not_found", keywords={"require_mechanisms": True}, view=None)
            return

        async def on_select(item: discord.ui.Select, new_interaction: discord.Interaction):
            nation = self.get_nation(int(item.values[0]))
            await new_interaction.response.defer()

            async def on_accept(_: discord.ui.Button, i: discord.Interaction):
                await i.response.defer()
                await func(nation, *args, **kwargs)

            async def on_reject(_: discord.ui.Button, i: discord.Interaction):
                await i.response.defer()
                await interaction.display(
                    "nation_lookup",
                    keywords={"nations": nations, "require_mechanisms": True},
                    callables={"on_select": on_select},
                )

            await interaction.display(
                "nation_preview",
                keywords={"nation": nation, "require_mechanisms": True},
                callables={"on_accept": on_accept, "on_reject": on_reject},
            )

        await interaction.display(
            "nation_lookup",
            keywords={"nations": nations, "require_mechanisms": True},
            callables={"on_select": on_select},
        )


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
