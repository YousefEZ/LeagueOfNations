from typing import Literal

import discord
import qalib
import qalib.interaction
from discord import app_commands
from discord.ext import commands
from host.base_types import UserId
from host.nation import Nation
from lon import LeagueOfNations
from qalib.template_engines.jinja2 import Jinja2
from sqlalchemy.orm import Session
from view.cogs.custom_jinja2 import ENVIRONMENT

StartMessages = Literal["start", "NonAscii"]


class Start(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    @app_commands.command(name="start", description="Found Your Nation")
    @app_commands.describe(nation_name="The name of your nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/start.xml")
    async def start(
        self, ctx: qalib.interaction.QalibInteraction[StartMessages], nation_name: str
    ) -> None:
        """Slash Command that founds a nation with the nation_name if it does not exist

        Args:
            ctx (qalib.QalibInteraction[StartMessages]): The context of the interaction
            nation_name (str): The name of the nation
        """

        async def confirm_start(_: discord.ui.Button, interaction: discord.Interaction):
            with Session(self.bot.engine) as session:
                Nation.start(UserId(ctx.user.id), nation_name, session)
            await interaction.response.send_message(":white_check_mark: Confirmed")

        async def decline_start(_: discord.ui.Button, interaction: discord.Interaction):
            await interaction.response.send_message(":x: Declined")

        if not nation_name.isascii():
            await ctx.rendered_send("NonAscii")
            return

        await ctx.rendered_send(
            "start",
            callables={"confirm": confirm_start, "decline": decline_start},
            keywords={"nation_name": nation_name},
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Start(bot))
