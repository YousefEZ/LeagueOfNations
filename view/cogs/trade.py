from typing import Dict, Literal
from discord import app_commands
import discord
from discord.ext import commands
from host.nation.types.resources import Resources
import qalib
import qalib.interaction
from qalib.template_engines.jinja2 import Jinja2

from host.nation import Nation
from host.nation.trade import TradeSentResponses
from lon import LeagueOfNations, interaction_morph
from view.cogs.custom_jinja2 import ENVIRONMENT


TradeRequestMessages = Literal[
    "trade_sent", "cannot_trade_with_self", "trade_too_many_active_agreements"
]

TradeRequestMapping: Dict[TradeSentResponses, TradeRequestMessages] = {
    TradeSentResponses.SUCCESS: "trade_sent",
    TradeSentResponses.CANNOT_TRADE_WITH_SELF: "cannot_trade_with_self",
    TradeSentResponses.TOO_MANY_ACTIVE_AGREEMENTS: "trade_too_many_active_agreements",
}


class Trade(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    trade_group = app_commands.Group(name="trade", description="Group related to trade commands")

    async def send_trade_offer(
        self, ctx: qalib.interaction.QalibInteraction, target: Nation
    ) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        response = nation.trade.send(target.identifier)
        await ctx.display(
            TradeRequestMapping[response],
            keywords={"sponsor": nation, "recipient": target, "Resources": Resources},
        )

    @trade_group.command(name="offer", description="Offer a trade to another user")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
    async def offer(self, ctx: qalib.interaction.QalibInteraction) -> None:
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
        async def target(
            interaction: qalib.interaction.QalibInteraction[TradeRequestMessages], nation: Nation
        ):
            @interaction_morph
            async def accept(i: discord.Interaction):
                await i.response.defer()
                await self.send_trade_offer(interaction, nation)

            @interaction_morph
            async def decline(i: discord.Interaction):
                await i.response.defer()
                await interaction.display(
                    "trade_decline", keywords={"sponsor": self.bot.get_nation(ctx.user.id)}
                )

            await interaction.display(
                "trade_offer",
                keywords={
                    "sponsor": self.bot.get_nation(ctx.user.id),
                    "recipient": nation,
                    "Resources": Resources,
                },
                callables={"accept": accept, "decline": decline},
            )

        await self.bot.get_user_target(ctx, target)


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Trade(bot))
