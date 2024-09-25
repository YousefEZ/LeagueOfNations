from __future__ import annotations


from dataclasses import dataclass
import traceback
import argparse
from functools import wraps
import logging
import os
import sys
from typing import (
    Awaitable,
    Callable,
    Concatenate,
    Coroutine,
    Generic,
    Literal,
    Optional,
    TypeVar,
)
import forge
import qalib
from qalib.translators.deserializer import K_contra
from qalib.translators.view import CheckEvent
from typing_extensions import ParamSpec

import discord
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from host import base_types
import host.base_models
from host.base_types import UserId
from host.nation import Nation
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


def interaction_morph(
    func: Callable[[discord.Interaction], Awaitable[None]],
) -> Callable[[discord.ui.Item, discord.Interaction], Awaitable[None]]:
    @wraps(func)
    async def f(_: discord.ui.Item, interaction: discord.Interaction) -> None:
        await func(interaction)

    return f


T = TypeVar("T")
K = TypeVar("K")
I = TypeVar("I", bound=discord.ui.Item, contravariant=True)


class LonCog(commands.Cog):
    bot: LeagueOfNations

    def __init__(self, bot: LeagueOfNations):
        self.bot = bot


@dataclass(frozen=True)
class Event(Generic[K_contra]):
    ctx: qalib.interaction.QalibInteraction[K_contra]
    bot: LeagueOfNations


class EventProtocol(Generic[K_contra]):
    ctx: qalib.interaction.QalibInteraction[K_contra]
    bot: LeagueOfNations


def event_with_session(
    method: Callable[Concatenate[K, Session, P], Coroutine[None, None, T]],
) -> Callable[Concatenate[K, P], Coroutine[None, None, T]]:
    @wraps(method)
    async def wrapper(self, *args: P.args, **kwargs: P.kwargs) -> T:
        logging.debug(
            "[EVENT][CALL] name=%s event_name=%s, args=%s, kwargs=%s",
            method.__name__,
            self,
            args,
            kwargs,
        )
        with Session(self.bot.engine) as session:
            try:
                return await method(self, session, *args, **kwargs)
            except Exception as e:
                logging.error(
                    "[ERROR] name=%s, traceback: %s, exception: %s",
                    method.__name__,
                    traceback.format_exc(),
                    e,
                )
                raise e

    return wrapper


def with_session(engine: Engine):
    def decorator(
        function: Callable[Concatenate[Session, P], Coroutine[None, None, T]],
    ) -> Callable[P, Coroutine[None, None, T]]:
        @wraps(function)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            with Session(engine) as session:
                try:
                    return await function(session, *args, **kwargs)
                except Exception as e:
                    logging.error(
                        "[ERROR] name=%s, traceback: %s, exception: %s",
                        function.__name__,
                        traceback.format_exc(),
                        e,
                    )
                    raise e

        return wrapper

    return decorator


def cog_with_session(
    method: Callable[
        Concatenate[commands.Cog, discord.Interaction, Session, P], Coroutine[None, None, T]
    ],
) -> Callable[Concatenate[commands.Cog, discord.Interaction, P], Coroutine[None, None, T]]:
    # This is a hacky way to forge the signature of the method so that discord.py can accept it
    @wraps(method, updated=tuple())
    @forge.delete("session")
    @forge.copy(method)
    async def wrapper(self, ctx: discord.Interaction, *args: P.args, **kwargs: P.kwargs) -> T:
        with Session(self.bot.engine) as session:
            try:
                return await method(self, ctx, session, *args, **kwargs)
            except Exception as e:
                logging.error(
                    "[ERROR] name=%s, traceback: %s, exception: %s",
                    method.__name__,
                    traceback.format_exc(),
                    e,
                )
                raise e

    return wrapper


def user_registered(
    method: Callable[
        Concatenate[commands.Cog, discord.Interaction, Session, P], Coroutine[None, None, None]
    ],
):
    @wraps(method)
    async def wrapper(
        self, ctx: discord.Interaction, session: Session, *args: P.args, **kwargs: P.kwargs
    ) -> None:
        user = Nation(base_types.UserId(ctx.user.id), session)
        if not user.exists:
            await ctx.response.send_message(
                ":x: You are not registered. Please use /start to register."
            )
        else:
            await method(self, ctx, session, *args, **kwargs)

    return wrapper


class LeagueOfNations(commands.AutoShardedBot):
    def __init__(self, engine: Engine):
        super().__init__(
            command_prefix="-",
            owner_id=251351879408287744,
            reconnect=True,
            case_insensitive=True,
            intents=discord.Intents.all(),
        )
        self.engine: Engine = engine
        self.notification_renderer = NotificationRenderer(self)

    async def setup_hook(self) -> None:
        self.loop.create_task(self.ready())

    def get_nation(self, user_id: int, session: Session) -> Nation:
        """Get the nation of the user with that user identifier

        Args:
            user_id (UserId): The ID of the user to get

        Returns (discord.User): The user
        """
        return Nation(UserId(user_id), session)

    def get_nation_from_name(self, nation_name: str, session: Session) -> Optional[Nation]:
        return Nation.fetch_from_name(nation_name, session)

    async def ready(self):
        await self.wait_until_ready()

        try:
            for cog in cogs:
                await self.load_extension(f"view.cogs.{cog}")
        except Exception as e:
            logging.info("*[CLIENT][LOADING_EXTENSION][STATUS] ERROR ", e)
        else:
            logging.info("*[CLIENT][LOADING_EXTENSION][STATUS] SUCCESS")

        await self.tree.sync()
        self.notification_renderer.start()
        logging.info("*[CLIENT][NOTIFICATIONS][STATUS] READY")

    def ensure_user(self, user: int) -> CheckEvent:
        async def check(_: discord.ui.View, interaction: discord.Interaction) -> bool:
            return interaction.user.id == user

        return check


if __name__ == "__main__":
    parser = argparse.ArgumentParser(prog="lon", description="Run the league of nations bot")
    parser.add_argument("--log", type=str)
    parser.add_argument(
        "-l",
        "--level",
        choices=logging.getLevelNamesMapping().keys(),
        default="INFO",
    )
    parser.add_argument("-db", "--database")

    args = parser.parse_args()
    if args.log:
        assert args.log.endswith(".log"), "LOG FILE MUST END WITH .log"
        logging.basicConfig(filename=args.log, level=logging.getLevelNamesMapping()[args.level])
    else:
        logging.basicConfig(stream=sys.stdout, level=logging.getLevelNamesMapping()[args.level])
    load_dotenv()

    TOKEN = os.getenv("DISCORD_TOKEN")
    URL = os.getenv("DATABASE_URL")
    assert TOKEN is not None, "MISSING TOKEN IN .env FILE"
    assert URL is not None, "MISSING DATABASE_URL IN .env FILE"

    engine = create_engine(URL, echo=False)

    host.base_models.Base.metadata.create_all(engine)
    LeagueOfNations(engine).run(token=TOKEN)
