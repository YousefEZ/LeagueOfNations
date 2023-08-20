import traceback
from typing import Literal

import discord
import qalib
from discord import app_commands
from discord.ext import commands
from qalib.template_engines.jinja2 import Jinja2

from host.nation import Nation
from host.nation.interior import UnitExchangeProtocol
from host.nation.types.interior import PurchaseResult
from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT

InfrastructureMessages = Literal["cost", "insufficient_funds", "success"]
EconomyMessages = Literal["balance", InfrastructureMessages]
UnitActions = Literal["buy", "sell"]

PositiveInteger = discord.app_commands.Range[int, 1]


class Economy(commands.Cog):

    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    @app_commands.command(name="balance", description="Check the balance of you Nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/economy.xml")
    async def balance(self, ctx: qalib.QalibInteraction[EconomyMessages]) -> None:
        """Balance command that shows the balance of the nations funds

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
        """
        nation = self.bot.get_nation(ctx.user.id)
        await ctx.rendered_send("balance", keywords={"nation": nation})

    async def buy(
            self,
            ctx: qalib.QalibInteraction[EconomyMessages],
            nation: Nation,
            unit: UnitExchangeProtocol,
            amount: PositiveInteger
    ) -> None:
        """Buy command that buys an item

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
            nation (Nation): the nation that is buying the unit
            unit (UnitExchangeProtocol): The unit to buy
            amount (int): The amount to buy
        """

        price = unit.price_order(amount)

        async def buy_confirmation(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            try:
                result = unit.buy(amount)
                if result == PurchaseResult.INSUFFICIENT_FUNDS:
                    await ctx.display("insufficient_funds",
                                      keywords={"nation": nation, "amount": amount, "price": price})
                elif result == PurchaseResult.SUCCESS:
                    await ctx.display("success", keywords={"nation": nation, "amount": amount, "price": price})
            except Exception as e:
                print(e)
                print(traceback.format_exc())

        await ctx.display("cost",
                          keywords={"nation": nation, 'amount': amount, 'price': price},
                          callables={"confirm": buy_confirmation})

    @app_commands.command(name="infrastructure", description="handling infrastructure of the nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/infrastructure.xml")
    async def infrastructure(
            self,
            ctx: qalib.QalibInteraction[EconomyMessages],
            action: UnitActions,
            amount: PositiveInteger
    ) -> None:
        """Infrastructure command that shows the infrastructure of the nation

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
            action (UnitActions): The action to perform
            amount (int): The amount to perform the action on. Defaults to None.
        """
        nation = self.bot.get_nation(ctx.user.id)
        if action == "buy":
            await self.buy(ctx, nation, nation.interior.infrastructure, amount)
        elif action == "sell":
            result = nation.interior.infrastructure.sell(amount)
            if result == PurchaseResult.INSUFFICIENT_FUNDS:
                await ctx.rendered_send("insufficient_amount", keywords={"nation": nation})
            elif result == PurchaseResult.SUCCESS:
                await ctx.rendered_send("success", keywords={"nation": nation})


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Economy(bot))
