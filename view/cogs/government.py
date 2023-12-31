from typing import Literal, cast

import discord
from host.nation.types.government import GovernmentTypes
import qalib
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from qalib.template_engines.jinja2 import Jinja2

from host.nation.types.boosts import BoostsLookup
from host.nation.government import Governments
from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT


UnitActions = Literal["buy", "sell"]
PositiveInteger = discord.app_commands.Range[int, 1]

GovernmentMessages = Literal["list", "display", "set", "error", "new_government"]


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
        ctx: qalib.QalibInteraction[GovernmentMessages],
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
        ctx: qalib.QalibInteraction[GovernmentMessages],
        government: Choice[str],
    ) -> None:
        await ctx.display("display", keywords={"government": Governments[government.value]})

    @government_group.command(name="set", description="Setting the government of the nation")
    @app_commands.choices(
        government=[Choice(name=f"{government.emoji} {name}", value=name) for name, government in Governments.items()]
    )
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/government.xml")
    async def government_set(
        self,
        ctx: qalib.QalibInteraction[GovernmentMessages],
        government: Choice[str],
    ) -> None:
        nation = self.bot.get_nation(ctx.user.id)
        government_type = cast(GovernmentTypes, government.value)
        if not nation.exists:
            await ctx.display("error", keywords={"error": "You don't have a nation"})
            return

        async def set_confirmation(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            difference = BoostsLookup.combine(Governments[government_type].boosts, nation.government.type.boosts.inverse())
            nation.government.set(government_type)
            await ctx.display(
                "new_government",
                keywords={"nation": nation, "government": Governments[government_type], "difference": difference},
            )

        await ctx.display(
            "set",
            keywords={"nation": nation, "government": Governments[government_type]},
            callables={"confirm": set_confirmation, "decline": delete},
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Government(bot))
