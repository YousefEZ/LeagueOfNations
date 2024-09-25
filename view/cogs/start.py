import logging
from typing import Dict, Literal

from dataclasses import dataclass
import discord
import qalib
import qalib.interaction
from discord import app_commands
from discord.ext import commands
from qalib.translators.view import ViewEvents

from host.gameplay_settings import GameplaySettings
from host.base_types import as_user_id
from host.nation import Nation, StartResponses
from lon import Event, LeagueOfNations, event_with_session
from qalib.template_engines.jinja2 import Jinja2
from sqlalchemy.orm import Session
from view.cogs.custom_jinja2 import ENVIRONMENT
from view.check import ensure_user


StartMessages = Literal[
    "start",
    "already_exists",
    "name_taken",
    "confirmation",
    "name_too_short",
    "name_too_long",
    "non_ascii_name",
]

StartMapping: Dict[StartResponses, StartMessages] = {
    StartResponses.SUCCESS: "confirmation",
    StartResponses.ALREADY_EXISTS: "already_exists",
    StartResponses.NAME_TAKEN: "name_taken",
    StartResponses.NAME_TOO_SHORT: "name_too_short",
    StartResponses.NAME_TOO_LONG: "name_too_long",
    StartResponses.NON_ASCII: "non_ascii_name",
}


@dataclass(frozen=True)
class StartEvent(Event[StartMessages]):
    nation_name: str

    @event_with_session
    async def confirm(
        self, session: Session, _: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        response = Nation.start(as_user_id(interaction.user.id), self.nation_name, session)
        logging.debug(
            "[START] UserId=%s, NationName=%s Response=%s",
            interaction.user.id,
            self.nation_name,
            response,
        )
        await interaction.response.defer()
        await self.ctx.display(
            StartMapping[response], keywords={"nation_name": self.nation_name}, view=None
        )

    async def decline(self, _: discord.ui.Button, interaction: discord.Interaction) -> None:
        await interaction.response.send_message(":x: Declined")


class Start(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    @app_commands.command(name="start", description="Found Your Nation")
    @app_commands.describe(nation_name="The name of your nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/start.xml")
    async def start(
        self,
        ctx: qalib.interaction.QalibInteraction[StartMessages],
        nation_name: app_commands.Range[
            str,
            GameplaySettings.metadata.minimum_nation_name_length,
            GameplaySettings.metadata.maximum_nation_name_length,
        ],
    ) -> None:
        """Slash Command that founds a nation with the nation_name

        Args:
            ctx (qalib.QalibInteraction[StartMessages]): The context of the interaction
            nation_name (str): The name of the nation
        """

        event = StartEvent(ctx, self.bot, nation_name)

        await ctx.display(
            "start",
            callables={"confirm_start": event.confirm, "decline": event.decline},
            keywords={"nation_name": nation_name},
            events={ViewEvents.ON_CHECK: ensure_user(ctx.user.id)},
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Start(bot))
