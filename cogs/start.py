from typing import Literal

import sqlalchemy
from discord.ext import commands

from qalib import qalib_context
from qalib.template_engines import formatter

from host.player import Player

NameTooLong = Literal["name_too_long"]
NameTooShort = Literal["name_too_short"]
NationStarted = Literal["start"]


class Start(commands.Cog):
    """Cog that is handles the start command, and the creation of a new player"""

    def __init__(self, bot, engine: sqlalchemy.Engine):
        self.bot = bot
        self._engine = engine

    @commands.command()
    @qalib_context(formatter.Formatter(), "templates/start.xml")
    async def start(self, ctx, *args):
        name = ' '.join(args)

        if len(name) < 3:
            await ctx.rendered_send(NameTooShort, name)
            return

        if len(name) > 75:
            await ctx.rendered_send(NameTooLong, name)
            return

        Player.start(ctx.message.author.id, name, self._engine)
        await ctx.rendered_send(NationStarted, name)


def setup(bot):
    bot.add_cog(Start(bot, bot.database))
