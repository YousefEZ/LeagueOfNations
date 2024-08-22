import datetime
from typing import Dict, Literal, Optional, cast
import discord
from discord.components import TextInput

from host import currency
from host import base_types
from host.base_types import UserId
from host.nation import Nation
import host.nation.foreign
from host.nation.foreign import AidAcceptCode, AidCancelCode, AidRejectCode, AidRequestCode
from host.notifier import Notification
import qalib
import qalib.interaction
from discord import app_commands
from discord.ext import commands
from qalib.template_engines.jinja2 import Jinja2
from qalib.translators.modal import ModalEvents

from lon import mechanisms_messages, LeagueOfNations, interaction_morph
from view.cogs.custom_jinja2 import ENVIRONMENT


AidSelectionMessages = Literal[
    "list",
    "requests",
    "display",
    "set",
    "error",
    "new_government",
    "reason",
    "view_aid",
    "view_sponsorship",
    "sponsorships",
    "aid_slots",
    "aid_slot",
]

PositiveInteger = discord.app_commands.Range[int, 1]

AidRequestMessages = Literal[
    "escrow",
    "confirm_aid",
    "player_not_exist",
    "same_as_sponsor",
    "insufficient_funds",
    "target_not_exist",
    "invalid_amount",
    "above_limit",
    "reason_not_ascii",
    "reason_too_long",
    "funds",
    "target_selection",
    mechanisms_messages,
]
AidAcceptMessages = Literal[
    "aid_accepted", "aid_not_exist", "not_a_recipient", "expired", "zero_slots"
]
AidCancelMessages = Literal["aid_cancelled", "aid_not_exist", "not_a_sponsor"]
AidRejectMessages = Literal["aid_rejected", "aid_not_exist", "not_a_recipient"]

AidMessages = Literal[AidRequestMessages, AidAcceptMessages, AidCancelMessages, AidRejectMessages]


aid_request_code_mapping: Dict[AidRequestCode, AidRequestMessages] = {
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

aid_accept_code_mapping: Dict[AidAcceptCode, AidAcceptMessages] = {
    AidAcceptCode.SUCCESS: "aid_accepted",
    AidAcceptCode.DOES_NOT_EXIST: "aid_not_exist",
    AidAcceptCode.NOT_THE_RECIPIENT: "not_a_recipient",
    AidAcceptCode.EXPIRED: "expired",
    AidAcceptCode.ZERO_SLOTS: "zero_slots",
}

aid_cancel_code_mapping: Dict[AidCancelCode, AidCancelMessages] = {
    AidCancelCode.SUCCESS: "aid_cancelled",
    AidCancelCode.DOES_NOT_EXIST: "aid_not_exist",
    AidCancelCode.NOT_A_SPONSOR: "not_a_sponsor",
}

aid_reject_code_mapping: Dict[AidRejectCode, AidRejectMessages] = {
    AidRejectCode.SUCCESS: "aid_rejected",
    AidRejectCode.DOES_NOT_EXIST: "aid_not_exist",
    AidRejectCode.NOT_THE_RECIPIENT: "not_a_recipient",
}


class Aid(commands.Cog):
    def __init__(self, bot: LeagueOfNations):
        self.bot = bot

    aid_group = app_commands.Group(name="aid", description="Group related to aid commands")

    async def send_aid(
        self,
        target: Nation,
        ctx: qalib.interaction.QalibInteraction[AidRequestMessages],
        amount: float,
    ) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_submit(modal, interaction: discord.Interaction) -> None:
            reason = cast(TextInput, modal.children[0]).value
            await interaction.response.defer()

            result, request = nation.foreign.send(
                UserId(target.identifier), currency.lnd(amount), reason or ""
            )
            if result == AidRequestCode.SUCCESS:
                await ctx.display(
                    aid_request_code_mapping[result],
                    keywords={"nation": nation, "target": target, "aid": request},
                )
                return
            await ctx.display(
                aid_request_code_mapping[result],
                keywords={"nation": nation, "target": target, "amount": currency.lnd(amount)},
                view=None,
            )

        @interaction_morph
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def confirm_aid(
            confirmed_ctx: qalib.interaction.QalibInteraction[AidSelectionMessages],
        ) -> None:
            await confirmed_ctx.rendered_send("reason", events={ModalEvents.ON_SUBMIT: on_submit})

        await ctx.display(
            "confirm_aid",
            keywords={"amount": currency.Currency(amount), "nation": nation, "target": target},
            callables={"confirm": confirm_aid},
        )

    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def get_funds(
        self,
        interaction: qalib.interaction.QalibInteraction[AidRequestMessages],
        ctx: qalib.interaction.QalibInteraction[AidRequestMessages],
        target_id: base_types.UserId,
    ) -> None:
        async def on_submit(modal, funds_interaction: discord.Interaction) -> None:
            amount = cast(TextInput, modal.children[0]).value
            assert amount is not None
            try:
                amount = float(amount)
            except ValueError:
                await funds_interaction.response.send_message("Amount is not valid")
            else:
                await funds_interaction.response.defer()
                await self.send_aid(self.bot.get_nation(target_id), ctx, amount)

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
        ctx: qalib.interaction.QalibInteraction[AidRequestMessages],
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
                    await self.send_aid(self.bot.get_nation(UserId(int(user_id))), ctx, funds)
                else:
                    await interaction.response.send_message("Amount is not valid")

        async def on_nation_submit(modal, interaction: discord.Interaction) -> None:
            nation_name = cast(TextInput, modal.children[0]).value
            funds = extract_funds(cast(TextInput, modal.children[1]).value)
            if funds is None:
                await interaction.response.send_message("Amount is not valid")
                return
            assert nation_name is not None
            await interaction.response.defer()
            await self.bot.get_user_from_nation_lookup(ctx, nation_name, self.send_aid, ctx, funds)

        @interaction_morph
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def open_id_modal(
            interaction: qalib.interaction.QalibInteraction[Literal["userid"]],
        ) -> None:
            await interaction.rendered_send("userid", events={ModalEvents.ON_SUBMIT: on_id_submit})

        @interaction_morph
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def open_nation_modal(
            interaction: qalib.interaction.QalibInteraction[Literal["nationselect"]],
        ) -> None:
            await interaction.rendered_send(
                "nationselect", events={ModalEvents.ON_SUBMIT: on_nation_submit}
            )

        async def on_user_select(
            item: discord.ui.UserSelect, interaction: discord.Interaction
        ) -> None:
            user = item.values[0]
            await self.get_funds(interaction, ctx, base_types.UserId(user.id))

        await ctx.display(
            "target_selection",
            callables={
                "userid": open_id_modal,
                "user_target": on_user_select,
                "nation": open_nation_modal,
            },
        )

    @aid_group.command(name="list", description="List all aid packages")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def list(
        self,
        ctx: qalib.interaction.QalibInteraction[
            Literal[AidSelectionMessages, AidAcceptMessages, AidRejectMessages]
        ],
    ) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_view(item: discord.ui.Select, interaction: discord.Interaction) -> None:
            aid_request = host.nation.foreign.AidRequest.from_id(item.values[0], self.bot.session)
            if aid_request is None:
                await ctx.display("error", keywords={"description": "Aid package not found"})
                return
            await interaction.response.defer()

            async def on_accept(_: discord.ui.Item, interaction: discord.Interaction) -> None:
                result, agreement = nation.foreign.accept(aid_request)
                await interaction.response.defer()
                if result == AidAcceptCode.SUCCESS and agreement is not None:
                    notification = Notification(
                        agreement.sponsor,
                        datetime.datetime.now(),
                        f"Aid package of {aid_request.amount} sent to {nation.name} has been accepted",
                    )
                    self.bot.notification_renderer.notifier.schedule(notification)
                await ctx.display(
                    aid_accept_code_mapping[result], keywords={"nation": nation, "aid": agreement}
                )

            async def on_reject(_: discord.ui.Item, interaction: discord.Interaction) -> None:
                await interaction.response.defer()
                result = nation.foreign.reject(aid_request)
                notification = Notification(
                    aid_request.sponsor,
                    datetime.datetime.now(),
                    f"Aid package of {aid_request.amount} sent to {nation.name} has been rejected",
                )
                self.bot.notification_renderer.notifier.schedule(notification)
                await ctx.display(
                    aid_reject_code_mapping[result], keywords={"nation": nation, "aid": aid_request}
                )

            await ctx.display(
                "view_aid",
                keywords={"aid": aid_request, "nation": nation},
                callables={"accept": on_accept, "reject": on_reject},
            )

        await ctx.display(
            "requests", keywords={"nation": nation}, callables={"select-aid": on_view}
        )

    @aid_group.command(name="sponsorships", description="list aid sponsorships")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def sponsorships(
        self,
        ctx: qalib.interaction.QalibInteraction[Literal[AidSelectionMessages, AidCancelMessages]],
    ) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_view(item: discord.ui.Select, interaction: discord.Interaction) -> None:
            package = host.nation.foreign.AidRequest.from_id(item.values[0], self.bot.session)
            if package is None:
                await ctx.display("error", keywords={"description": "Aid package not found"})
                return
            await interaction.response.defer()

            async def on_cancel(_: discord.ui.Item, interaction: discord.Interaction) -> None:
                await interaction.response.defer()
                result = nation.foreign.cancel(package)
                await ctx.display(
                    aid_cancel_code_mapping[result], keywords={"nation": nation, "aid": package}
                )

            await ctx.display(
                "view_sponsorship",
                keywords={"aid": package, "nation": nation},
                callables={"cancel": on_cancel},
            )

        await ctx.display(
            "sponsorships", keywords={"nation": nation}, callables={"select-aid": on_view}
        )

    @aid_group.command(name="slots", description="list aid slots")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def slots(self, ctx: qalib.interaction.QalibInteraction[AidSelectionMessages]) -> None:
        nation = self.bot.get_nation(ctx.user.id)

        async def on_aid_select(item: discord.ui.Select, interaction: discord.Interaction) -> None:
            await interaction.response.defer()
            await ctx.display(
                "aid_slot",
                keywords={
                    "nation": nation,
                    "aid": host.nation.foreign.AidAgreement.from_id(
                        item.values[0], self.bot.session
                    ),
                },
            )

        await ctx.display(
            "aid_slots", keywords={"nation": nation}, callables={"select-aid": on_aid_select}
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Aid(bot))
