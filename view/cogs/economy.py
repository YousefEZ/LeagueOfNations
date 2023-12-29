import traceback
from typing import Literal, Dict, Callable, Coroutine

import discord
import qalib
from discord import app_commands
from discord.app_commands import Choice
from discord.ext import commands
from qalib.template_engines.jinja2 import Jinja2

from host.nation import Nation
from host.nation.interior import UnitExchangeProtocol, K
from host.nation.types.improvements import Improvements
from host.nation.types.transactions import PurchaseResult, SellResult
from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT

ImprovementActions = Literal["display", "buy", "sell"]
UnitActions = Literal["buy", "sell"]
PositiveInteger = discord.app_commands.Range[int, 1]

InfrastructureMessages = Literal["cost", "insufficient_funds", "success"]
EconomyMessages = Literal["balance", InfrastructureMessages]
PurchaseMessages = Literal["cost", "insufficient_funds", "success"]
SellMessages = Literal["cashback", "insufficient_amount", "success"]

purchase_mappings: Dict[PurchaseResult, PurchaseMessages] = {
    PurchaseResult.INSUFFICIENT_FUNDS: "insufficient_funds",
    PurchaseResult.SUCCESS: "buy_success",
}

sell_mappings: Dict[SellResult, SellMessages] = {
    SellResult.INSUFFICIENT_AMOUNT: "insufficient_amount",
    SellResult.SUCCESS: "sell_success",
}

UnitTypes = Literal["infrastructure", "land", "technology"]
unit_exchange_mappings: Dict[UnitTypes, Callable[[Nation], UnitExchangeProtocol]] = {
    "infrastructure": lambda nation: nation.infrastructure,
    "land": lambda nation: nation.land,
    "technology": lambda nation: nation.technology,
}

ExchangeMessages = Literal[PurchaseMessages, SellMessages]
ImprovementMessages = Literal["owned", "display", PurchaseMessages, SellMessages]


async def delete(interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    await interaction.delete_original_response()


class Economy(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot
        self._unit_actions_mapping: Dict[
            UnitActions,
            Callable[
                [
                    qalib.QalibInteraction[ExchangeMessages],
                    Nation,
                    UnitExchangeProtocol[K],
                    PositiveInteger,
                ],
                Coroutine[None, None, None],
            ],
        ] = {"buy": self.buy, "sell": self.sell}

    @app_commands.command(name="balance", description="Check the balance of you Nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/economy.xml")
    async def balance(self, ctx: qalib.QalibInteraction[EconomyMessages]) -> None:
        """Balance command that shows the balance of the nations funds

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
        """
        nation = self.bot.get_nation(ctx.user.id)
        await ctx.rendered_send("balance", keywords={"nation": nation})

    @staticmethod
    async def buy(
        ctx: qalib.QalibInteraction[PurchaseMessages],
        nation: Nation,
        unit: UnitExchangeProtocol[K],
        amount: PositiveInteger,
    ) -> None:
        """Buy command that buys an item

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
            nation (Nation): the nation that is buying the units
            unit (UnitExchangeProtocol): The unit to buy
            amount (int): The amount to buy
        """

        price = unit.price_order(amount)

        async def buy_confirmation(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            await ctx.display(
                purchase_mappings[unit.buy(amount)],
                keywords={"nation": nation, "amount": amount, "price": price},
            )

        await ctx.display(
            "cost",
            keywords={"nation": nation, "amount": amount, "price": price},
            callables={"confirm": buy_confirmation, "decline": delete},
        )

    @staticmethod
    async def sell(
        ctx: qalib.QalibInteraction[SellMessages],
        nation: Nation,
        unit: UnitExchangeProtocol,
        amount: PositiveInteger,
    ) -> None:
        """Sell command that sells an item

        Args:
            ctx (qalib.QalibInteraction[EconomyMessages]): The context of the interaction
            nation (Nation): the nation that is selling the units
            unit (UnitExchangeProtocol): The unit to sell
            amount (int): The amount to sell
        """

        units = unit.amount
        cashback = unit.price_order(amount)

        async def sell_confirmation(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            await ctx.display(
                sell_mappings[unit.sell(amount)],
                keywords={
                    "nation": nation,
                    "amount": amount,
                    "cashback": cashback,
                    "units": units,
                },
            )

        await ctx.display(
            "cashback",
            keywords={"nation": nation, "amount": amount, "cashback": cashback},
            callables={"confirm": sell_confirmation, "decline": delete},
        )

    @app_commands.command(name="infrastructure", description="handling infrastructure of the nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/infrastructure.xml")
    async def infrastructure(
        self,
        ctx: qalib.QalibInteraction[ExchangeMessages],
        action: UnitActions,
        amount: PositiveInteger,
    ) -> None:
        """Infrastructure command that shows the infrastructure of the nation

        Args:
            ctx (qalib.QalibInteraction[ExchangeMessages]): The context of the interaction
            action (UnitActions): The action to perform
            amount (int): The amount to perform the action on. Defaults to None.
        """
        nation = self.bot.get_nation(ctx.user.id)
        await self._unit_actions_mapping[action](ctx, nation, nation.interior.infrastructure, amount)

    @app_commands.command(name="technology", description="handling technology of the nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/technology.xml")
    async def technology(
        self,
        ctx: qalib.QalibInteraction[ExchangeMessages],
        action: UnitActions,
        amount: PositiveInteger,
    ) -> None:
        """Technology command that shows the technology of the nation

        Args:
            ctx (qalib.QalibInteraction[ExchangeMessages]): The context of the interaction
            action (UnitActions): The action to perform
            amount (int): The amount to perform the action on. Defaults to None.
        """
        nation = self.bot.get_nation(ctx.user.id)
        await self._unit_actions_mapping[action](ctx, nation, nation.interior.technology, amount)

    @app_commands.command(name="land", description="handling land of the nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/land.xml")
    async def land(
        self,
        ctx: qalib.QalibInteraction[ExchangeMessages],
        action: UnitActions,
        amount: PositiveInteger,
    ) -> None:
        """Land command that shows the land of the nation

        Args:
            ctx (qalib.QalibInteraction[ExchangeMessages]): The context of the interaction
            action (UnitActions): The action to perform
            amount (int): The amount to perform the action on. Defaults to None.
        """
        nation = self.bot.get_nation(ctx.user.id)
        await self._unit_actions_mapping[action](ctx, nation, nation.interior.land, amount)

    improvement_group = app_commands.Group(name="improvement", description="This is a group")

    @improvement_group.command(name="display", description="Displaying the possible improvements")
    @app_commands.choices(
        improvement=[
            Choice(name=f"{improvement.emoji} {name}", value=name) for name, improvement in Improvements.items()
        ]
    )
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/improvement.xml")
    async def improvement(
        self,
        ctx: qalib.QalibInteraction[ImprovementMessages],
        improvement: Choice[str],
    ) -> None:
        """Improvement command that shows the improvements of the nation

        Args:
            ctx (qalib.QalibInteraction[ImprovementMessages]): The context of the interaction
            improvement (Choice[str]): The improvement to buy
        """
        await ctx.display(
            "display",
            keywords={
                "improvement": Improvements[improvement.value],
                "improvements": Improvements,
            },
        )

    @improvement_group.command(name="owned", description="Displaying the owned improvements")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/improvement.xml")
    async def improvement_owned(
        self,
        ctx: qalib.QalibInteraction[ImprovementMessages],
    ) -> None:
        """Improvement command that shows the improvements of the nation

        Args:
            ctx (qalib.QalibInteraction[ImprovementMessages]): The context of the interaction
        """
        nation = self.bot.get_nation(ctx.user.id)
        await ctx.display(
            "owned",
            keywords={
                "nation_name": nation.metadata.nation_name,
                "improvements": nation.improvements,
            },
        )

    @improvement_group.command(name="buy", description="Buying an improvement")
    @app_commands.choices(
        improvement=[
            Choice(name=f"{improvement.emoji} {name}", value=improvement.name)
            for name, improvement in Improvements.items()
        ]
    )
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/improvement.xml")
    async def improvement_buy(
        self,
        ctx: qalib.QalibInteraction[ImprovementMessages],
        improvement: Choice[str],
        amount: PositiveInteger,
    ) -> None:
        """Improvement command that shows the improvements of the nation

        Args:
            ctx (qalib.QalibInteraction[ImprovementMessages]): The context of the interaction
            improvement (Choice[str]): The improvement to buy
            amount (PositiveInteger): The amount to buy
        """
        nation = self.bot.get_nation(ctx.user.id)
        improvement_class = Improvements[improvement.value]

        async def confirm(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            result = nation.improvements.buy(improvement_class, amount)
            await ctx.display(
                purchase_mappings[result],
                keywords={
                    "improvement": improvement_class,
                    "amount": amount,
                    "nation": nation,
                },
            )

        await ctx.display(
            "cost",
            keywords={
                "improvement": improvement_class,
                "amount": amount,
                "nation": nation,
            },
            callables={"confirm": confirm, "decline": delete},
        )

    @improvement_group.command(name="sell", description="Selling an improvement")
    @app_commands.choices(
        improvement=[
            Choice(name=f"{improvement.emoji} {name}", value=improvement.name)
            for name, improvement in Improvements.items()
        ]
    )
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/improvement.xml")
    async def improvement_sell(
        self,
        ctx: qalib.QalibInteraction[ImprovementMessages],
        improvement: Choice[str],
        amount: PositiveInteger,
    ) -> None:
        """Improvement command that shows the improvements of the nation

        Args:
            ctx (qalib.QalibInteraction[ImprovementMessages]): The context of the interaction
            improvement (Choice[str]): The improvement to sell
            amount (PositiveInteger): The amount to sell
        """
        nation = self.bot.get_nation(ctx.user.id)
        improvement_class = Improvements[improvement.value]

        async def confirm(interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            try:
                result = nation.improvements.sell(improvement_class, amount)
                await ctx.display(
                    sell_mappings[result],
                    keywords={
                        "improvement": improvement_class,
                        "amount": amount,
                        "nation": nation,
                    },
                )
            except Exception as e:
                print(e)
                traceback.print_tb(e.__traceback__)

        await ctx.display(
            "cashback",
            keywords={
                "improvement": improvement_class,
                "amount": amount,
                "nation": nation,
            },
            callables={"confirm": confirm, "decline": delete},
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Economy(bot))
