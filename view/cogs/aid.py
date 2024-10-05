import logging
from typing import Dict, Literal, Optional, cast
import discord
from discord.components import TextInput
from sqlalchemy.orm import Session

from host import currency
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

from lon import cog_with_session, lookup_messages, LeagueOfNations, interaction_morph
from view.lookup import cog_find_nation
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
    lookup_messages,
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
        ctx: qalib.interaction.QalibInteraction[AidRequestMessages],
        *,
        sponsor: Nation,
        recipient: Nation,
        amount: currency.Price,
    ) -> None:
        async def on_submit(modal, interaction: discord.Interaction) -> None:
            reason = cast(TextInput, modal.children[0]).value
            await interaction.response.defer()
            logging.debug(
                "[AID][SENDING][FUND] Sponsor=%s, Funds=%s, Recipient=%s",
                ctx.user.id,
                amount,
                recipient.identifier,
            )
            result = sponsor.foreign.send(UserId(recipient.identifier), amount, reason or "")
            await ctx.display(
                aid_request_code_mapping[result],
                keywords={"nation": sponsor, "target": recipient, "amount": amount},
            )

        @interaction_morph
        @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
        async def confirm_aid(
            confirmed_ctx: qalib.interaction.QalibInteraction[AidSelectionMessages],
        ) -> None:
            await confirmed_ctx.rendered_send("reason", events={ModalEvents.ON_SUBMIT: on_submit})

        await ctx.display(
            "confirm_aid",
            keywords={"amount": amount, "nation": sponsor, "target": recipient},
            callables={"confirm": confirm_aid},
        )

    @aid_group.command(name="send", description="Send aid to another nation")
    @cog_with_session
    @cog_find_nation("recipient")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def send(
        self,
        ctx: qalib.interaction.QalibInteraction[AidRequestMessages],
        session: Session,
        recipient: Nation,
    ) -> None:
        def extract_funds(raw_funds: Optional[str]) -> Optional[currency.Price]:
            if raw_funds is None:
                return None
            try:
                amount = currency.Price(float(raw_funds))
            except ValueError:
                return None
            else:
                return amount

        async def on_submit(modal, interaction: discord.Interaction) -> None:
            funds = extract_funds(cast(TextInput, modal.children[0]).value)

            if funds is None:
                await interaction.response.send_message("Amount is not valid")
                return
            await interaction.response.defer()
            await self.send_aid(
                ctx,
                sponsor=Nation(UserId(ctx.user.id), session),
                recipient=recipient,
                amount=funds,
            )

        await ctx.rendered_send("funds", events={ModalEvents.ON_SUBMIT: on_submit}, view=None)

    @aid_group.command(name="list", description="List all aid packages")
    @cog_with_session
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def list(
        self,
        ctx: qalib.interaction.QalibInteraction[
            Literal[AidSelectionMessages, AidAcceptMessages, AidRejectMessages]
        ],
        session: Session,
    ) -> None:
        nation = Nation(UserId(ctx.user.id), session)

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
                        f"Aid package of {aid_request.amount} sent to {nation.name} has been accepted",
                    )
                    await self.bot.notification_renderer.render(notification)
                await ctx.display(
                    aid_accept_code_mapping[result], keywords={"nation": nation, "aid": agreement}
                )

            async def on_reject(_: discord.ui.Item, interaction: discord.Interaction) -> None:
                await interaction.response.defer()
                result = nation.foreign.reject(aid_request)
                notification = Notification(
                    aid_request.sponsor,
                    f"Aid package of {aid_request.amount} sent to {nation.name} has been rejected",
                )
                await self.bot.notification_renderer.render(notification)
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
    @cog_with_session
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def sponsorships(
        self,
        ctx: qalib.interaction.QalibInteraction[Literal[AidSelectionMessages, AidCancelMessages]],
        session: Session,
    ) -> None:
        nation = Nation(UserId(ctx.user.id), session)

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
    @cog_with_session
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/aid.xml")
    async def slots(
        self, ctx: qalib.interaction.QalibInteraction[AidSelectionMessages], session: Session
    ) -> None:
        nation = Nation(UserId(ctx.user.id), session)

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
