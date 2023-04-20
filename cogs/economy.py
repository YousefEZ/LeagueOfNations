from typing import Literal

import qalib
from discord import app_commands
from discord.ext import commands
from qalib.template_engines import formatter

from lon import LeagueOfNations

EconomyMessages = Literal["balance"]


class Economy(commands.Cog):

    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    @commands.command()
    async def sync(self, ctx):
        await ctx.bot.tree.sync(guid=ctx.guild)
        await ctx.send("Synced")

    @app_commands.command(name="balance", description="Check the balance of you Nation")
    @qalib.qalib_interaction(formatter.Formatter(), "templates/balance.xml")
    async def balance(self, ctx: qalib.QalibInteraction[EconomyMessages]) -> None:
        """Balance command that shows the balance of the nations funds

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
        """
        nation = self.bot.get_nation(ctx.user.id)
        await ctx.rendered_send("balance", keywords={"nation": nation})
