import logging
from typing import Dict, Literal, ParamSpec, TypeVar
from discord import app_commands
import discord
from qalib.translators import Callback
from qalib.translators.view import ViewEvents
from sqlalchemy.orm import Session
from host.base_types import as_user_id
from host.nation.types.resources import ResourceName, Resources
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
from lon import LeagueOfNations, LonCog, interaction_morph, cog_with_session, with_session
from view.lookup import cog_find_nation
from view.cogs.custom_jinja2 import ENVIRONMENT


T = TypeVar("T")
P = ParamSpec("P")


TradeErrorMessages = Literal["too_many_active_agreements", "sponsor_too_many_active_agreements"]

TradeSelectMessages = Literal["select_resources", "select_trade_active_agreement"]

TradeOfferMessages = Literal[
    TradeErrorMessages,
    "trade_sent",
    "cannot_trade_with_self",
    "select_resources",
    "trade_cancel",
    "trade_offer",
]

TradeViewMessages = Literal["trades", "trade_view"]

TradeCancelMessages = Literal["trade_cancel"]

TradeOfferingMapping: Dict[TradeSentResponses, TradeOfferMessages] = {
    TradeSentResponses.SUCCESS: "trade_sent",
    TradeSentResponses.CANNOT_TRADE_WITH_SELF: "cannot_trade_with_self",
    TradeSentResponses.TOO_MANY_ACTIVE_AGREEMENTS: "too_many_active_agreements",
}

TradeSelectMapping: Dict[TradeSelectResponses, TradeSelectMessages] = {
    TradeSelectResponses.SUCCESS: "select_resources",
    TradeSelectResponses.ACTIVE_AGREEMENT: "select_trade_active_agreement",
}

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

TradeCancelMapping: Dict[TradeCancelResponses, TradeCancelMessages] = {}


class Trade(LonCog):
    trade_group = app_commands.Group(name="trade", description="Group related to trade commands")

    @trade_group.command(name="select", description="Select resources to trade")
    @cog_with_session
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
    async def select(self, ctx: qalib.interaction.QalibInteraction, session: Session) -> None:
        def resource_select_with(resource: ResourceName) -> Callback:
            @with_session(self.bot.engine)
            async def callback(
                session: Session, select: discord.ui.Select, interaction: discord.Interaction
            ) -> None:
                await interaction.response.defer()
                nation = self.bot.get_nation(ctx.user.id, session)
                result = nation.trade.swap_resources(resource, select.values[0])

                if result is TradeSelectResponses.SUCCESS:
                    await ctx.display(TradeSelectMapping[result])
                    return
                resources = nation.trade.resources
                await ctx.display(
                    "select_resources",
                    keywords={"Resources": Resources, "nation": nation, "resources": resources},
                    callables={resource: resource_select_with(resource) for resource in resources},
                )

            return callback

        nation = self.bot.get_nation(ctx.user.id, session)
        resources = nation.trade.resources
        await ctx.display(
            "select_resources",
            keywords={"Resources": Resources, "nation": nation, "resources": resources},
            callables={resource: resource_select_with(resource) for resource in resources},
        )

    async def send_trade_offer(
        self, ctx: qalib.interaction.QalibInteraction, *, sponsor: Nation, recipient: Nation
    ) -> None:
        response = sponsor.trade.send(recipient.identifier)
        logging.info(
            "[TRADE][OFFER][SENDING] Sponsor=%s, Recipient=%s, Response=%s",
            ctx.user.id,
            recipient.identifier,
            response,
        )
        await ctx.display(
            TradeOfferingMapping[response],
            keywords={"sponsor": sponsor, "recipient": recipient, "Resources": Resources},
            events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
        )

    @trade_group.command(name="offer", description="Offer a trade to another user")
    @cog_with_session
    @cog_find_nation("recipient")
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
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

        @interaction_morph
        @with_session(self.bot.engine)
        async def accept(session: Session, i: discord.Interaction):
            await i.response.defer()
            await self.send_trade_offer(
                ctx, sponsor=self.bot.get_nation(ctx.user.id, session), recipient=recipient
            )

        @interaction_morph
        async def decline(_: discord.Interaction):
            logging.info(
                "[TRADE][OFFER][CANCELLED] Sponsor=%s, Recipient=%s",
                ctx.user.id,
                recipient.identifier,
            )
            await ctx.delete_original_response()

        await ctx.display(
            "trade_offer",
            keywords={
                "sponsor": self.bot.get_nation(ctx.user.id, session),
                "recipient": recipient,
                "Resources": Resources,
            },
            callables={"accept": accept, "decline": decline},
            events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
        )

    @trade_group.command(name="requests", description="View trade offers")
    @cog_with_session
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
    async def requests(
        self, ctx: qalib.interaction.QalibInteraction[TradeRequestMessages], session: Session
    ) -> None:
        async def on_trade_request_select(
            select: discord.ui.Select, interaction: discord.Interaction
        ):
            logging.debug(
                "[TRADE][REQUEST][SELECTED] UserId=%s, Partner=%s", ctx.user.id, select.values[0]
            )
            await interaction.response.defer()

            @interaction_morph
            @with_session(self.bot.engine)
            async def on_accept(session: Session, i: discord.Interaction):
                recipient = Nation(as_user_id(ctx.user.id), session)
                sponsor = Nation(as_user_id(select.values[0]), session)
                response = recipient.trade.accept(sponsor.identifier)

                logging.debug(
                    "[TRADE][REQUEST][ACCEPT] Recipient=%s, Sponsor=%s, Response=%s",
                    recipient.identifier,
                    sponsor.identifier,
                    response,
                )

                await i.response.defer()
                if response is TradeAcceptResponses.SUCCESS:
                    notification = Notification(
                        sponsor.identifier,
                        f"Trade Offer to {nation.metadata.emoji} {nation.name} has been accepted",
                    )
                    await self.bot.notification_renderer.render(notification)

                await ctx.display(
                    TradeAcceptMapping[response],
                    keywords={"recipient": recipient, "sponsor": sponsor},
                )

            @interaction_morph
            @with_session(self.bot.engine)
            async def on_decline(session: Session, _: discord.Interaction):
                recipient = Nation(as_user_id(ctx.user.id), session)
                sponsor = Nation(as_user_id(select.values[0]), session)
                response = nation.trade.decline(sponsor.identifier)

                logging.debug(
                    "[TRADE][REQUEST][DECLINE] Recipient=%s, Sponsor=%s, Response=%s",
                    recipient.identifier,
                    sponsor.identifier,
                    response,
                )
                if response is TradeDeclineResponses.SUCCESS:
                    notification = Notification(
                        sponsor.identifier,
                        f"Trade Offer to {nation.metadata.emoji} {nation.name} has been declined",
                    )
                    await self.bot.notification_renderer.render(notification)
                await ctx.display(
                    TradeDeclineMapping[response],
                    keywords={"recipient": recipient, "sponsor": sponsor},
                    events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
                )

            recipient = Nation(as_user_id(ctx.user.id), session)
            sponsor = Nation(as_user_id(select.values[0]), session)
            await ctx.display(
                "trade_offer_selected",
                keywords={"recipient": recipient, "sponsor": sponsor, "Resources": Resources},
                callables={"accept": on_accept, "decline": on_decline},
                events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
            )

        nation = Nation(as_user_id(ctx.user.id), session)
        await ctx.display(
            "trade_requests",
            keywords={"nation": nation, "Resources": Resources},
            callables={"trade_identifier": on_trade_request_select},
            events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
        )

    @trade_group.command(name="view", description="Cancel a trade offer")
    @cog_with_session
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/trade.xml")
    async def view(
        self,
        ctx: qalib.interaction.QalibInteraction[Literal[TradeViewMessages, TradeCancelMessages]],
        session: Session,
    ) -> None:
        @with_session(self.bot.engine)
        async def on_trade_select(
            session: Session, select: discord.ui.Select, interaction: discord.Interaction
        ):
            await interaction.response.defer()
            partner = Nation(as_user_id(select.values[0]), session)
            agreement = nation.trade.fetch_agreement_with(partner.identifier)
            logging.debug(
                "[TRADE][VIEW][SELECTED] UserId=%s, Partner=%s, Found=%s",
                nation.identifier,
                partner,
                agreement is not None,
            )
            assert agreement is not None, "Trade agreement not found"

            @interaction_morph
            @with_session(self.bot.engine)
            async def on_cancel(session: Session, _: discord.Interaction):
                nation = Nation(as_user_id(ctx.user.id), session)
                response = nation.trade.cancel(partner.identifier)
                logging.debug(
                    "[TRADE][VIEW][CANCELLED] Recipient=%s, Sponsor=%s, Response=%s",
                    agreement.recipient,
                    agreement.sponsor,
                    response,
                )
                if response is TradeCancelResponses.SUCCESS:
                    await self.bot.notification_renderer.render(
                        Notification(
                            partner.identifier,
                            f"Trade Offer Cancelled with {nation.metadata.emoji} {nation.name}",
                        )
                    )
                await ctx.display(
                    TradeCancelMapping[response],
                    keywords={"nation": nation, "partner": partner},
                )

            await ctx.display(
                "trade_view",
                keywords={
                    "agreement": agreement,
                    "nation": nation,
                    "partner": partner,
                    "Resources": Resources,
                },
                callables={"cancel": on_cancel},
                events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
            )

        nation = self.bot.get_nation(ctx.user.id, session)
        await ctx.display(
            "trades",
            keywords={"nation": nation, "Resources": Resources},
            callables={"trade_identifier": on_trade_select},
            events={ViewEvents.ON_CHECK: self.bot.ensure_user(ctx.user.id)},
        )


async def setup(bot: LeagueOfNations) -> None:
    await bot.add_cog(Trade(bot))
