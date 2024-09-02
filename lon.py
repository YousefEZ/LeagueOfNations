from __future__ import annotations

from functools import wraps
import logging
import os
from typing import Awaitable, Callable, Coroutine, Literal, Optional, Protocol, cast
from discord.components import TextInput
import qalib
from qalib.template_engines.jinja2 import Jinja2
from qalib.translators.modal import ModalEvents
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
from view.cogs.custom_jinja2 import ENVIRONMENT
from view.notifications import NotificationRenderer

cogs = "start", "economy", "search", "trade", "government", "aid"
connect_to_db = False

lookup_messages = Literal[
    "nation_lookup",
    "nation_preview",
    "lookup_nation_name_not_found",
    "lookup_nation_id_not_found",
    "target_selection",
    "get_user_id",
    "closed",
    "nation_select",
]

P = ParamSpec("P")


class Selector(Protocol):
    async def __call__(
        self,
        nation: Nation,
        interaction: QalibInteraction[lookup_messages],
        accept_override=None,
        reject_override=None,
    ): ...


def interaction_morph(
    func: Callable[[discord.Interaction], Awaitable[None]],
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
        interaction: QalibInteraction[lookup_messages],
        user_id: int,
        func: Callable[Concatenate[Nation, P], Coroutine[None, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        nation = self.get_nation(user_id)
        if not nation.exists:
            await interaction.display(
                "lookup_nation_id_not_found", keywords={"require_lookup": True}, view=None
            )
            return

        async def on_accept(_: discord.ui.Button, i: discord.Interaction):
            await i.response.defer()
            await func(nation, *args, **kwargs)

        async def on_reject(_: discord.ui.Button, i: discord.Interaction):
            await i.response.defer()
            await interaction.response.send_message("Cancelled")

        await interaction.display(
            "nation_preview",
            keywords={"nation": nation, "require_lookup": True},
            callables={"on_accept": on_accept, "on_reject": on_reject},
        )

    def preview_and_return_nation(
        self,
        func: Callable[Concatenate[discord.Interaction, Nation, P], Coroutine[None, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ) -> Selector:
        async def confirmation(
            nation: Nation,
            interaction: qalib.interaction.QalibInteraction[lookup_messages],
            accept_override=None,
            reject_override=None,
        ):
            async def on_accept(_: discord.ui.Button, i: discord.Interaction):
                await func(i, nation, *args, **kwargs)

            async def on_reject(_: discord.ui.Button, i: discord.Interaction):
                await i.response.defer()
                await interaction.display("closed", keywords={"require_lookup": True}, embed=None)

            await interaction.display(
                "nation_preview",
                keywords={"nation": nation, "require_lookup": True},
                callables={
                    "on_accept": accept_override if accept_override else on_accept,
                    "on_reject": reject_override if reject_override else on_reject,
                },
            )

        return confirmation

    async def get_user_target(
        self,
        ctx: QalibInteraction[lookup_messages],
        func: Callable[Concatenate[discord.Interaction, Nation, P], Coroutine[None, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        selector = self.preview_and_return_nation(func, *args, **kwargs)

        async def on_id_submit(modal: discord.ui.Modal, interaction: discord.Interaction) -> None:
            user_id = cast(TextInput, modal.children[0]).value
            assert user_id is not None
            await interaction.response.defer()
            if not user_id.isdigit():
                await interaction.response.send_message("User ID is not valid")
            elif not self.get_nation(int(user_id)).exists:
                await interaction.response.send_message("User does not have a nation")
            else:
                await selector(self.get_nation(int(user_id)), ctx)

        async def on_nation_submit(modal, interaction: discord.Interaction) -> None:
            nation_name = cast(TextInput, modal.children[0]).value
            assert nation_name is not None
            await interaction.response.defer()
            await self.get_user_from_nation_lookup(ctx, nation_name, func, *args, **kwargs)

        @interaction_morph
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
        async def open_id_modal(
            interaction: qalib.interaction.QalibInteraction[lookup_messages],
        ) -> None:
            await interaction.rendered_send(
                "get_user_id",
                events={ModalEvents.ON_SUBMIT: on_id_submit},
                keywords={"require_lookup": True},
            )

        @interaction_morph
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
        async def open_nation_modal(
            interaction: qalib.interaction.QalibInteraction[lookup_messages],
        ) -> None:
            await interaction.rendered_send(
                "nation_select",
                events={ModalEvents.ON_SUBMIT: on_nation_submit},
                keywords={"require_lookup": True},
            )

        async def on_user_select(
            item: discord.ui.UserSelect,
            i: discord.Interaction,
        ) -> None:
            user = item.values[0]
            await i.response.defer()
            await selector(self.get_nation(UserId(user.id)), ctx)

        await ctx.display(
            "target_selection",
            callables={
                "userid": open_id_modal,
                "user_target": on_user_select,
                "nation": open_nation_modal,
            },
            keywords={"require_lookup": True},
        )

    async def get_user_from_nation_lookup(
        self,
        interaction: QalibInteraction[lookup_messages],
        nation_name: str,
        func: Callable[Concatenate[discord.Interaction, Nation, P], Coroutine[None, None, None]],
        *args: P.args,
        **kwargs: P.kwargs,
    ):
        nations = Nation.search_for_nations(nation_name, self.session)

        selection = self.preview_and_return_nation(func, *args, **kwargs)
        if not nations:
            await interaction.display(
                "lookup_nation_name_not_found", keywords={"require_lookup": True}, view=None
            )
            return

        async def on_select(item: discord.ui.Select, new_interaction: discord.Interaction):
            nation = self.get_nation(int(item.values[0]))
            await new_interaction.response.defer()

            async def on_reject(_: discord.ui.Button, i: discord.Interaction):
                await i.response.defer()
                await interaction.display(
                    "nation_lookup",
                    keywords={"nations": nations, "require_lookup": True},
                    callables={"on_select": on_select},
                )

            await selection(nation, interaction, reject_override=on_reject)

        await interaction.display(
            "nation_lookup",
            keywords={"nations": nations, "require_lookup": True},
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
