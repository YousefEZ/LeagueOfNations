import traceback
from typing import Literal

import discord
import qalib
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from qalib.template_engines.jinja2 import Jinja2

from host.nation.types.improvements import Improvements
from host.nation.government import Governments
from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT


UnitActions = Literal["buy", "sell"]
PositiveInteger = discord.app_commands.Range[int, 1]

Mess = Literal["Test"]


async def delete(interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    await interaction.delete_original_response()


class Government(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    government_group = app_commands.Group(name="government", description="Group related to government commands")

    @government_group.command(name="list", description="Describing the possible governments")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/government.xml")
    async def government_list(
        self,
        ctx: qalib.QalibInteraction[Mess],
    ) -> None:
        """Government command that shows the governments of the nation

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
        """
        await ctx.display("list", keywords={"governments": Governments})

    @government_group.command(name="display", description="Displaying the possible governments")
    @app_commands.choices(
        government=[Choice(name=f"{government.emoji} {name}", value=name) for name, government in Governments.items()]
    )
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/government.xml")
    async def government_display(
        self,
        ctx: qalib.QalibInteraction[Mess],
        government: Choice[str],
    ) -> None:
        print(Governments[government.value].boosts.pretty_print())
        await ctx.display("display", keywords={"government": Governments[government.value]})


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Government(bot))
