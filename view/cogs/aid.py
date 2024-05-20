import datetime
from typing import Callable, Coroutine, Literal, Optional, cast
import discord
from discord.components import TextInput
from functools import wraps

from host import currency
from host import base_types
from host.base_types import UserId
from host.nation import Nation
import host.nation.foreign
from host.nation.foreign import AidAcceptCode, AidCancelCode, AidRejectCode, AidRequestCode
from host.notifier import Notification
import qalib
from discord import app_commands
from discord.ext import commands
from qalib.template_engines.jinja2 import Jinja2
from qalib.translators.modal import ModalEvents

from host.nation import Nation
from lon import LeagueOfNations
from view.cogs.custom_jinja2 import ENVIRONMENT


PositiveInteger = discord.app_commands.Range[int, 1]

AidSelectionMessages = Literal["list", "display", "set", "error", "new_government", "reason"]

AidAcceptMessages = Literal["not_a_recipient", "insufficient_funds", "expired", "success", "zero_slots"]

AidRequestMessages = Literal["success", "same_as_sponsor", "insufficient_funds", "invalid_recipient", "invalid_amount"]

AidMessages = Literal[
    AidAcceptMessages,
    "cannot_be_sponsor",
    "success",
    "insufficient_funds",
    "invalid_recipient",
    "invalid_amount",
]


async def delete(interaction: discord.Interaction) -> None:
    await interaction.response.defer()
    await interaction.delete_original_response()


class AidPackage:
    def __init__(self, nation: Nation, amount: int):
        self.recipient = nation
        self.amount = amount


PositiveInteger = discord.app_commands.Range[int, 1]


def interaction_button(
    func: Callable[[discord.Interaction], Coroutine[None, None, None]]
) -> Callable[[discord.ui.Button, discord.Interaction], Coroutine[None, None, None]]:
    @wraps(func)
    async def f(item: discord.ui.Button, interaction: discord.Interaction) -> None:
        await func(interaction)

    return f


aid_request_code_mapping = {
    AidRequestCode.SUCCESS: "escrow",
    AidRequestCode.PLAYER_NOT_EXISTS: "player_not_exist",
    AidRequestCode.SAME_AS_SPONSOR: "same_as_sponsor",
    AidRequestCode.INSUFFICIENT_FUNDS: "insufficient_funds",
    AidRequestCode.INVALID_RECIPIENT: "target_not_exist",
    AidRequestCode.INVALID_AMOUNT: "invalid_amount",
    AidRequestCode.ABOVE_LIMIT: "above_limit",
    AidRequestCode.REASON_NOT_ASCII: "reason_not_ascii",
    AidRequestCode.REASON_TOO_LONG: "reason_too_long",
}

aid_accept_code_mapping = {
    AidAcceptCode.SUCCESS: "aid_accepted",
}

aid_cancel_code_mapping = {
    AidCancelCode.SUCCESS: "aid_cancelled",
}

aid_reject_code_mapping = {
    AidRejectCode.SUCCESS: "aid_rejected",
}


class Aid(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    aid_group = app_commands.Group(name="aid", description="Group related to aid commands")

    async def send_aid(self, ctx: qalib.QalibInteraction[AidSelectionMessages], target_id: str, amount: float) -> None:
        nation = self.bot.get_nation(ctx.user.id)
        target = self.bot.get_nation(int(target_id))

        async def on_submit(modal, interaction: discord.Interaction) -> None:
            reason = cast(TextInput, modal.children[0]).value
            await interaction.response.defer()

            result, request = nation.foreign.send(UserId(target.identifier), currency.lnd(amount), reason)
            if result == AidRequestCode.SUCCESS:
                await ctx.display(
                    aid_request_code_mapping[result], keywords={"nation": nation, "target": target, "aid": request}
                )
                return
            await ctx.display(
                aid_request_code_mapping[result],
                keywords={"nation": nation, "target": target, "amount": currency.lnd(amount)},
                view=None,
            )

        @interaction_button
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def confirm_aid(confirmed_ctx: qalib.QalibInteraction[AidSelectionMessages]) -> None:
            await confirmed_ctx.rendered_send("reason", events={ModalEvents.ON_SUBMIT: on_submit})

        await ctx.display(
            "confirm_aid",
            keywords={"amount": amount * currency.Currency, "nation": nation, "target": target},
            callables={"confirm": confirm_aid},
        )

    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def get_funds(
        self,
        interaction: qalib.QalibInteraction[AidSelectionMessages],
        ctx: qalib.QalibInteraction[AidSelectionMessages],
        target_id: str,
    ) -> None:
        print("getting funds")

        async def on_submit(modal, funds_interaction: discord.Interaction) -> None:
            amount = cast(TextInput, modal.children[0]).value
            assert amount is not None
            try:
                amount = float(amount)
            except ValueError:
                await funds_interaction.response.send_message("Amount is not valid")
            else:
                await funds_interaction.response.defer()
                await self.send_aid(ctx, target_id, amount)

        target = self.bot.get_nation(base_types.UserId(int(target_id)))
        if not target.exists:
            await interaction.response.defer()
            await ctx.display(aid_request_code_mapping[AidRequestCode.INVALID_RECIPIENT])
            return

        await interaction.rendered_send("funds", events={ModalEvents.ON_SUBMIT: on_submit})

    @aid_group.command(name="send", description="Send aid to another nation")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def send(
        self,
        ctx: qalib.QalibInteraction[AidSelectionMessages],
    ) -> None:
        def extract_funds(raw_funds: Optional[str]) -> Optional[float]:
            if raw_funds is None:
                return None
            try:
                amount = float(raw_funds)
            except ValueError:
                return None
            else:
                return amount

        async def on_id_submit(modal, interaction: discord.Interaction) -> None:
            user_id = cast(TextInput, modal.children[0]).value
            assert user_id is not None
            await interaction.response.defer()
            if not user_id.isdigit():
                await interaction.response.send_message("User ID is not valid")
            elif not self.bot.get_nation(int(user_id)).exists:
                await interaction.response.send_message("User does not have a nation")
            else:
                funds = extract_funds(cast(TextInput, modal.children[1]).value)
                if funds is not None:
                    await self.send_aid(ctx, user_id, funds)
                else:
                    await interaction.response.send_message("Amount is not valid")

        async def on_nation_submit(modal, interaction: discord.Interaction) -> None:
            nation_name = cast(TextInput, modal.children[0]).value
            assert nation_name is not None
            await interaction.response.defer()
            nation = self.bot.get_nation_from_name(nation_name)

            if nation is None:
                await interaction.response.send_message(f"Nation: {nation_name} does not exist")
                return

            funds = extract_funds(cast(TextInput, modal.children[1]).value)
            if funds is not None:
                await self.send_aid(ctx, str(nation.identifier), funds)
            else:
                await interaction.response.send_message("Amount is not valid")

        @interaction_button
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def open_id_modal(interaction: qalib.QalibInteraction[AidSelectionMessages]) -> None:
            await interaction.rendered_send("userid", events={ModalEvents.ON_SUBMIT: on_id_submit})

        @interaction_button
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def open_nation_modal(interaction: qalib.QalibInteraction[AidSelectionMessages]) -> None:
            await interaction.rendered_send("nation_modal", events={ModalEvents.ON_SUBMIT: on_id_submit})

        async def on_user_select(item: discord.ui.UserSelect, interaction: discord.Interaction) -> None:
            print("on user select")
            user = item.values[0]
            await self.get_funds(interaction, ctx, str(user.id))

        await ctx.display("target_selection", callables={"userid": open_id_modal, "user_target": on_user_select})

    @aid_group.command(name="list", description="List all aid packages")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def list(self, ctx: qalib.QalibInteraction[AidSelectionMessages]) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_view(item: discord.ui.UserSelect, interaction: discord.Interaction) -> None:
            aid_request = host.nation.foreign.AidRequest.from_id(item.values[0], self.bot.session)
            if aid_request is None:
                await ctx.display("error", keywords={"description": "Aid package not found"})
                return
            await interaction.response.defer()

            async def on_accept(_: discord.ui.Item, interaction: qalib.QalibInteraction[AidSelectionMessages]) -> None:
                result, agreement = nation.foreign.accept(aid_request)
                await interaction.response.defer()
                if result == AidAcceptCode.SUCCESS and agreement is not None:
                    notification = Notification(
                        agreement.sponsor,
                        datetime.datetime.now(),
                        f"Aid package of {aid_request.amount} sent to {nation.name} has been accepted",
                    )
                    self.bot.notification_renderer.notifier.schedule(notification)
                await ctx.display(aid_accept_code_mapping[result], keywords={"nation": nation, "aid": agreement})

            async def on_reject(_: discord.ui.Item, interaction: qalib.QalibInteraction[AidSelectionMessages]) -> None:
                await interaction.response.defer()
                result = nation.foreign.reject(aid_request)
                notification = Notification(
                    aid_request.sponsor,
                    datetime.datetime.now(),
                    f"Aid package of {aid_request.amount} sent to {nation.name} has been rejected",
                )
                self.bot.notification_renderer.notifier.schedule(notification)
                await ctx.display(aid_reject_code_mapping[result], keywords={"nation": nation, "aid": aid_request})

            await ctx.display(
                "view-aid",
                keywords={"aid": aid_request, "nation": nation},
                callables={"accept": on_accept, "reject": on_reject},
            )

        await ctx.display("requests", keywords={"nation": nation}, callables={"select-aid": on_view})

    @aid_group.command(name="sponsorships", description="list aid sponsorships")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def sponsorships(self, ctx: qalib.QalibInteraction[AidSelectionMessages]) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_view(item: discord.ui.UserSelect, interaction: discord.Interaction) -> None:
            package = host.nation.foreign.AidRequest.from_id(item.values[0], self.bot.session)
            if package is None:
                await ctx.display("error", keywords={"description": "Aid package not found"})
                return
            await interaction.response.defer()

            async def on_cancel(_: discord.ui.Item, interaction: qalib.QalibInteraction[AidSelectionMessages]) -> None:
                await interaction.response.defer()
                result = nation.foreign.cancel(package)
                await ctx.display(aid_cancel_code_mapping[result], keywords={"nation": nation, "aid": package})

            await ctx.display(
                "view-sponsorship", keywords={"aid": package, "nation": nation}, callables={"cancel": on_cancel}
            )

        await ctx.display("sponsorships", keywords={"nation": nation}, callables={"select-aid": on_view})

    @aid_group.command(name="slots", description="list aid slots")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def slots(self, ctx: qalib.QalibInteraction[AidSelectionMessages]) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_aid_select(item: discord.ui.Select, interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            await ctx.display(
                "aid_slot",
                keywords={
                    "nation": nation,
                    "aid": host.nation.foreign.AidAgreement.from_id(item.values[0], self.bot.session),
                },
            )

        await ctx.display("aid-slots", keywords={"nation": nation}, callables={"select-aid": on_aid_select})


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Aid(bot))
