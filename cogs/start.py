from typing import Literal

import discord
import qalib
from discord import app_commands
from discord.ext import commands
from qalib.template_engines import formatter
from sqlalchemy.engine import Engine

from lon import LeagueOfNations

StartMessages = Literal["start"]


class Start(commands.Cog):

    def __init__(self, bot: LeagueOfNations, engine: Engine):
        self.bot = bot
        self.engine = engine

    async def confirm_start(self, interaction: discord.Interaction):
        connection = self.bot.connection
        await interaction.response.send_message(":white_check_mark: Confirmed")

    @staticmethod
    async def decline_start(interaction: discord.Interaction):
        await interaction.response.send_message(":x: Declined")

    @commands.command()
    async def sync(self, ctx):
        await ctx.bot.tree.sync(guid=ctx.guild)
        await ctx.send("Synced")

    @app_commands.command(name="start", description="Found Your Nation")
    @app_commands.describe(nation_name="The name of your nation")
    @qalib.qalib_interaction(formatter.Formatter(), "templates/start.xml")
    async def start(self, ctx: qalib.QalibInteraction[StartMessages], nation_name: str) -> None:
        """Slash Command that founds a nation with the nation_name if it does not exist

        Args:
            ctx (qalib.QalibInteraction[StartMessages]): The context of the interaction
            nation_name (str): The name of the nation
        """

        await ctx.rendered_send("start",
                                callables={"confirm": self.confirm_start, "decline": self.decline_start},
                                keywords={"nation_name": nation_name})


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Start(bot, bot.engine))
