from typing import Literal

import discord
from host.nation import Nation
import qalib
from discord import app_commands
from discord.ext import commands
from discord.ext.commands import BadArgument
from qalib.template_engines.jinja2 import Jinja2

from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT

SearchMessages = Literal["invalid_name", "search_results", "unrecognized", "statistics", "unrecognized_identifier"]


class Search(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    search_group = app_commands.Group(name="search", description="This is a group")

    class NameTransformer(app_commands.Transformer):
        async def transform(self, interaction: discord.Interaction, value: str) -> str:
            if value.isascii():
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

        nations = Nation.search_for_nations(name, self.bot.session, with_like=True)
        await ctx.rendered_send("search_results", keywords={"name": name, "nations": nations})

    @search_group.command(name="user", description="Search for a user")
    @qalib.qalib_interaction(
        Jinja2(ENVIRONMENT),
        "templates/search.xml",
    )
    async def search_user(self, ctx: qalib.QalibInteraction[SearchMessages], user: discord.User) -> None:
        nation = self.bot.get_nation(user.id)
        if not nation.exists:
            await ctx.rendered_send("unrecognized", keywords={"user": user})
            return
        await ctx.rendered_send("statistics", keywords={"nation": nation, "user": user.name})

    @search_group.command(name="id", description="Search for a user")
    @qalib.qalib_interaction(
        Jinja2(ENVIRONMENT),
        "templates/search.xml",
    )
    async def search_id(self, ctx: qalib.QalibInteraction[SearchMessages], identifier: int) -> None:
        nation = self.bot.get_nation(identifier)
        if not nation.exists:
            await ctx.rendered_send("unrecognized_identifier", keywords={"identifier": identifier})
            return
        user = self.bot.get_user(identifier)
        if user is None:
            await ctx.rendered_send("unknown_player", keywords={"nation": nation})
            return

        await ctx.rendered_send("statistics", keywords={"nation": nation, "user": user.name})


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Search(bot))
