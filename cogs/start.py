import sqlalchemy
from discord.ext import commands

from qalib import qalib_context, QalibContext
from qalib.template_engines import formatter

from host.player import Player

NameTooLong = "name_too_long"
NameTooShort = "name_too_short"
NationStarted = "start"


class Start(commands.Cog):
    """Cog that is handles the start command, and the creation of a new player"""

    def __init__(self, bot, engine: sqlalchemy.Engine):
        self.bot = bot
        self._engine = engine

    @commands.command()
    @qalib_context(formatter.Formatter(), "templates/start.xml")
    async def start(self, ctx: QalibContext, *args):
        name = ' '.join(args)

        if len(name) < 3:
            await ctx.rendered_send(NameTooShort, keywords={"name": name})
            return

        if len(name) > 75:
            await ctx.rendered_send(NameTooLong, keywords={"name": name})
            return

        Player.start(ctx.message.author.id, name, self._engine)
        await ctx.rendered_send(NationStarted, keywords={"name": name})


def setup(bot):
    bot.add_cog(Start(bot, bot.database))
