from discord import app_commands
from discord.ext import commands
import qalib
import qalib.interaction
from qalib.template_engines.jinja2 import Jinja2

from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT


class Trade(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    trade_group = app_commands.Group(name="trade", description="Group related to trade commands")

    @trade_group.command(name="offer", description="Offer a trade to another user")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
    async def offer(self, ctx: qalib.interaction.QalibInteraction) -> None:
        await ctx.rendered_send("Offering trade")


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Trade(bot))
