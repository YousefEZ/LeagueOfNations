from typing import Literal

import discord
import qalib
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import BadArgument
from qalib.template_engines.jinja2 import Jinja2

from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT

SearchMessages = Literal["invalid_name", "search_results"]


class Search(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    search_group = app_commands.Group(name="search", description="This is a group")

    class NameTransformer(app_commands.Transformer):
        async def transform(self, interaction: discord.Interaction, value: str) -> str:
            if all(ord(c) < 128 for c in value):
                return value

            raise BadArgument("Name must be ASCII")

    @search_group.command(name="nation", description="Search for an improvement")
    @qalib.qalib_interaction(
        Jinja2(ENVIRONMENT),
        "templates/search.xml",
    )
    async def search(self, ctx: qalib.QalibInteraction[SearchMessages], name: str) -> None:
        if not name.isascii():
            await ctx.rendered_send("invalid_name", keywords={"name": name})
            return

        nations = [self.bot.get_nation(ctx.user.id)]
        await ctx.rendered_send("search_results", keywords={"name": name, "nations": nations})


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Search(bot))
