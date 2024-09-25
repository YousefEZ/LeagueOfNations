from dataclasses import dataclass
from functools import partial
import logging
from typing import Any, Dict, Literal, ParamSpec, TypeVar
from discord import app_commands
import discord
from qalib.translators.view import ViewEvents
from sqlalchemy.orm import Session
from host import base_types
from host.base_types import as_user_id
from host.nation.types.resources import BonusResources, ResourceName, Resources
from host.notifier import Notification
import qalib
import qalib.interaction
from qalib.template_engines.jinja2 import Jinja2

from host.nation import Nation
from host.nation.trade import (
    TradeAcceptResponses,
    TradeCancelResponses,
    TradeDeclineResponses,
    TradeSelectResponses,
    TradeSentResponses,
)
from lon import (
    Event,
    LeagueOfNations,
    LonCog,
    event_with_session,
    cog_with_session,
    user_registered,
)
from view.check import ensure_user
from view.lookup import cog_find_nation
from view.cogs.custom_jinja2 import ENVIRONMENT


T = TypeVar("T")
P = ParamSpec("P")


TradeNotFound = Literal["trade_not_found"]

TradeErrorMessages = Literal[
    "too_many_active_agreements", "sponsor_too_many_active_agreements", TradeNotFound
]


TradeSelectMessages = Literal[
    "select_resources",
    "select_trade_active_agreement",
    "missing_resource",
    "duplicate_resource",
    "invalid_resource",
]


@dataclass(frozen=True)
class ResourceSwitch(Event[TradeSelectMessages]):
    resource: ResourceName

    @event_with_session
    async def __call__(
        self, session: Session, select: discord.ui.Select, interaction: discord.Interaction
    ) -> None:
        await interaction.response.defer()
        nation = Nation(as_user_id(self.ctx.user.id), session)
        result = nation.trade.swap_resources(self.resource, select.values[0])

        if result is TradeSelectResponses.SUCCESS:
            await self.ctx.display(TradeSelectMapping[result])
            return
        await self.ctx.display(
            "select_resources",
            keywords={"Resources": Resources, "nation": nation},
            callables={
                resource: ResourceSwitch(self.ctx, self.bot, resource)
                for resource in nation.trade.resources
            },
        )


TradeOfferMessages = Literal[
    TradeErrorMessages,
    "trade_offer",
    "trade_sent",
    "cannot_trade_with_self",
    "partner_not_found",
    "trade_partner_full",
]

TradeOfferingMapping: Dict[TradeSentResponses, TradeOfferMessages] = {
    TradeSentResponses.SUCCESS: "trade_sent",
    TradeSentResponses.CANNOT_TRADE_WITH_SELF: "cannot_trade_with_self",
    TradeSentResponses.TOO_MANY_ACTIVE_AGREEMENTS: "too_many_active_agreements",
    TradeSentResponses.PARTNER_NOT_FOUND: "partner_not_found",
    TradeSentResponses.TRADE_PARTNER_FULL: "trade_partner_full",
}


@dataclass(frozen=True)
class TradeOffer(Event[TradeOfferMessages]):
    recipient: base_types.UserId

    @event_with_session
    async def confirm(
        self, session: Session, _: discord.ui.Button, interaction: discord.Interaction
    ):
        logging.info(
            "[TRADE][OFFER][SENDING] Sponsor=%s, Recipient=%s",
            self.ctx.user.id,
            self.recipient,
        )
        await interaction.response.defer()
        sponsor = Nation(as_user_id(self.ctx.user.id), session)
        response = sponsor.trade.send(self.recipient)
        logging.info(
            "[TRADE][OFFER][SENT] Sponsor=%s, Recipient=%s, Response=%s",
            self.ctx.user.id,
            self.recipient,
            response,
        )
        await self.ctx.display(
            TradeOfferingMapping[response],
            keywords={
                "sponsor": sponsor,
                "recipient": Nation(self.recipient, session),
                "Resources": Resources,
            },
            events={ViewEvents.ON_CHECK: ensure_user(self.ctx.user.id)},
            view=None,
        )

    async def cancel(self, *_: Any) -> None:
        logging.info(
            "[TRADE][OFFER][CANCELLED] Sponsor=%s, Recipient=%s",
            self.ctx.user.id,
            self.recipient,
        )
        await self.ctx.delete_original_response()


TradeRequestMessages = Literal[
    TradeErrorMessages,
    "trade_offer_selected",
    "trade_requests",
    "trade_accepted",
    "trade_not_found",
    "trade_offer",
    "trade_decline",
    "trade_partner_full",
]

TradeAcceptMapping: Dict[TradeAcceptResponses, TradeRequestMessages] = {
    TradeAcceptResponses.SUCCESS: "trade_accepted",
    TradeAcceptResponses.NOT_FOUND: "trade_not_found",
    TradeAcceptResponses.TOO_MANY_ACTIVE_AGREEMENTS: "too_many_active_agreements",
}

TradeDeclineMapping: Dict[TradeDeclineResponses, TradeRequestMessages] = {
    TradeDeclineResponses.SUCCESS: "trade_decline",
    TradeDeclineResponses.NOT_FOUND: "trade_not_found",
}


class TradeRequestView(Event[TradeRequestMessages]):
    @event_with_session
    async def accept(
        self,
        session: Session,
        _: discord.ui.Button,
        interaction: discord.Interaction,
        sponsor_id: base_types.UserId,
    ) -> None:
        recipient = Nation(as_user_id(self.ctx.user.id), session)
        sponsor = Nation(sponsor_id, session)
        response = recipient.trade.accept(sponsor.identifier)

        logging.debug(
            "[TRADE][REQUEST][ACCEPT] Recipient=%s, Sponsor=%s, Response=%s",
            recipient.identifier,
            sponsor.identifier,
            response,
        )

        await interaction.response.defer()
        if response is TradeAcceptResponses.SUCCESS:
            notification = Notification(
                sponsor.identifier,
                f"Trade Offer to {recipient.metadata.emoji} {recipient.name} has been accepted",
            )
            await self.bot.notification_renderer.render(notification)

        await self.ctx.display(
            TradeAcceptMapping[response],
            keywords={"recipient": recipient, "sponsor": sponsor, "Resources": Resources},
            events={ViewEvents.ON_CHECK: ensure_user(self.ctx.user.id)},
            view=None,
        )

    @event_with_session
    async def decline(self, session: Session, *_: Any, sponsor_id: base_types.UserId) -> None:
        recipient = Nation(as_user_id(self.ctx.user.id), session)
        sponsor = Nation(sponsor_id, session)
        response = recipient.trade.decline(sponsor.identifier)

        logging.debug(
            "[TRADE][REQUEST][DECLINE] Recipient=%s, Sponsor=%s, Response=%s",
            recipient.identifier,
            sponsor.identifier,
            response,
        )
        if response is TradeDeclineResponses.SUCCESS:
            notification = Notification(
                sponsor.identifier,
                f"Trade Offer to {recipient.metadata.emoji} {recipient.name} has been declined",
            )
            await self.bot.notification_renderer.render(notification)
        await self.ctx.display(
            TradeDeclineMapping[response],
            keywords={"recipient": recipient, "sponsor": sponsor},
            events={ViewEvents.ON_CHECK: ensure_user(self.ctx.user.id)},
            view=None,
        )

    @event_with_session
    async def __call__(
        self, session: Session, select: discord.ui.Select, interaction: discord.Interaction
    ):
        logging.debug(
            "[TRADE][REQUEST][SELECTED] UserId=%s, Partner=%s", self.ctx.user.id, select.values[0]
        )
        await interaction.response.defer()
        recipient = Nation(as_user_id(self.ctx.user.id), session)
        sponsor_id = as_user_id(select.values[0])
        sponsor = Nation(sponsor_id, session)
        await self.ctx.display(
            "trade_offer_selected",
            keywords={"recipient": recipient, "sponsor": sponsor, "Resources": Resources},
            callables={
                "accept": partial(self.accept, sponsor_id=sponsor_id),
                "decline": partial(self.decline, sponsor_id=sponsor_id),
            },
            events={ViewEvents.ON_CHECK: ensure_user(self.ctx.user.id)},
        )


TradeSelectMapping: Dict[TradeSelectResponses, TradeSelectMessages] = {
    TradeSelectResponses.SUCCESS: "select_resources",
    TradeSelectResponses.ACTIVE_AGREEMENT: "select_trade_active_agreement",
    TradeSelectResponses.MISSING_RESOURCE: "missing_resource",
    TradeSelectResponses.DUPLICATE_RESOURCE: "duplicate_resource",
    TradeSelectResponses.INVALID_RESOURCE: "invalid_resource",
}

TradeViewMessages = Literal["trades", "trade_view"]

TradeCancelMessages = Literal["trade_cancel", TradeNotFound]

TradeCancelMapping: Dict[TradeCancelResponses, TradeCancelMessages] = {
    TradeCancelResponses.SUCCESS: "trade_cancel",
    TradeCancelResponses.NOT_FOUND: "trade_not_found",
}


class TradeView(Event[TradeViewMessages | TradeCancelMessages]):
    @event_with_session
    async def cancel(self, session: Session, *_: Any, partner_id: base_types.UserId) -> None:
        nation = Nation(as_user_id(self.ctx.user.id), session)
        partner = Nation(partner_id, session)
        response = nation.trade.cancel(partner.identifier)
        logging.debug(
            "[TRADE][VIEW][CANCELLED] UserId=%s, Partner=%s, Response=%s",
            nation.identifier,
            partner.identifier,
            response,
        )
        if response is TradeCancelResponses.SUCCESS:
            await self.bot.notification_renderer.render(
                Notification(
                    partner.identifier,
                    f"Trade Offer Cancelled with {nation.metadata.emoji} {nation.name}",
                )
            )
        await self.ctx.display(
            TradeCancelMapping[response],
            keywords={"nation": nation, "partner": partner},
            view=None,
        )

    @event_with_session
    async def __call__(
        self, session: Session, select: discord.ui.Select, interaction: discord.Interaction
    ) -> None:
        await interaction.response.defer()
        nation = Nation(as_user_id(self.ctx.user.id), session)
        partner = Nation(as_user_id(select.values[0]), session)
        agreement = nation.trade.fetch_agreement_with(partner.identifier)
        logging.debug(
            "[TRADE][VIEW][SELECTED] UserId=%s, Partner=%s, Found=%s",
            nation.identifier,
            partner,
            agreement is not None,
        )
        assert agreement is not None, "Trade agreement not found"

        await self.ctx.display(
            "trade_view",
            keywords={
                "agreement": agreement,
                "nation": nation,
                "partner": partner,
                "Resources": Resources,
                "BonusResources": BonusResources,
            },
            callables={"cancel": partial(self.cancel, partner_id=partner.identifier)},
            events={ViewEvents.ON_CHECK: ensure_user(self.ctx.user.id)},
        )


class Trade(LonCog):
    trade_group = app_commands.Group(name="trade", description="Group related to trade commands")

    @trade_group.command(name="select", description="Select resources to trade")
    @cog_with_session
    @user_registered
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade/select.xml")
    async def select(
        self, ctx: qalib.interaction.QalibInteraction[TradeSelectMessages], session: Session
    ) -> None:
        nation = Nation(as_user_id(ctx.user.id), session)
        await ctx.display(
            "select_resources",
            keywords={"Resources": Resources, "nation": nation},
            callables={
                resource: ResourceSwitch(ctx, self.bot, resource)
                for resource in nation.trade.resources
            },
        )

    @trade_group.command(name="offer", description="Offer a trade to another user")
    @cog_with_session
    @user_registered
    @cog_find_nation("recipient")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade/offer.xml")
    async def offer(
        self,
        ctx: qalib.interaction.QalibInteraction[TradeOfferMessages],
        session: Session,
        recipient: Nation,
    ) -> None:
        logging.debug(
            "[TRADE][OFFER][RECIPIENT] Opening Window from UserId=%s to Recipient=%s",
            ctx.user.id,
            recipient.identifier,
        )
        make_offer = TradeOffer(ctx, self.bot, recipient.identifier)
        await ctx.display(
            "trade_offer",
            keywords={
                "sponsor": Nation(as_user_id(ctx.user.id), session),
                "recipient": recipient,
                "Resources": Resources,
            },
            callables={"accept": make_offer.confirm, "decline": make_offer.cancel},
            events={ViewEvents.ON_CHECK: ensure_user(ctx.user.id)},
        )

    @trade_group.command(name="requests", description="View trade offers")
    @cog_with_session
    @user_registered
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade/request.xml")
    async def requests(
        self, ctx: qalib.interaction.QalibInteraction[TradeRequestMessages], session: Session
    ) -> None:
        nation = Nation(as_user_id(ctx.user.id), session)
        await ctx.display(
            "trade_requests",
            keywords={"nation": nation, "Resources": Resources},
            callables={"trade_identifier": TradeRequestView(ctx, self.bot)},
            events={ViewEvents.ON_CHECK: ensure_user(ctx.user.id)},
        )

    @trade_group.command(name="view", description="Cancel a trade offer")
    @cog_with_session
    @user_registered
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade/view.xml")
    async def view(
        self,
        ctx: qalib.interaction.QalibInteraction[Literal[TradeViewMessages, TradeCancelMessages]],
        session: Session,
    ) -> None:
        await ctx.display(
            "trades",
            keywords={"nation": Nation(as_user_id(ctx.user.id), session), "Resources": Resources},
            callables={"trade_identifier": TradeView(ctx, self.bot)},
            events={ViewEvents.ON_CHECK: ensure_user(ctx.user.id)},
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Trade(bot))
