from dataclasses import dataclass
from functools import wraps
import logging
import traceback
from typing import Protocol, cast, Literal, ParamSpec, Callable, Coroutine, Concatenate

import forge
import qalib
from qalib.interaction import QalibInteraction
from qalib.template_engines.jinja2 import Jinja2
from qalib.translators.view import ViewEvents
from qalib.translators.modal import ModalEvents
import discord
import discord.ui
from discord.ext import commands
from sqlalchemy.orm import Session

from host.base_types import UserId
from host.nation import Nation
from lon import (
    EventWithContext,
    LeagueOfNations,
    event_with_session,
    qalib_event_interaction,
)
from view.check import ensure_user
from view.cogs.custom_jinja2 import ENVIRONMENT

__all__ = ("cog_find_nation",)


lookup_messages = Literal[
    "nation_lookup",
    "nation_preview",
    "lookup_nation_name_not_found",
    "lookup_nation_id_not_found",
    "target_selection",
    "get_user_id",
    "closed",
    "nation_select",
]

P = ParamSpec("P")


class Selector(Protocol):
    async def __call__(
        self,
        nation: Nation,
        interaction: QalibInteraction[lookup_messages],
        accept_override=None,
        reject_override=None,
    ): ...


def _preview_and_return_nation(
    func: Callable[[UserId], Coroutine[None, None, None]],
) -> Selector:
    async def confirmation(
        nation: Nation,
        interaction: qalib.interaction.QalibInteraction[lookup_messages],
        accept_override=None,
        reject_override=None,
    ):
        async def on_accept(_: discord.ui.Button, i: discord.Interaction):
            logging.debug(
                "[LOOKUP][SELECTED] UserId=%s Selected=%s", interaction.user.id, nation.identifier
            )
            await i.response.defer()
            try:
                await func(nation.identifier)
            except Exception as e:
                logging.error(
                    "[LOOKUP][ERROR] Exception: %s, Traceback: %s", e, traceback.format_exc()
                )
                raise e

        async def on_reject(_: discord.ui.Button, i: discord.Interaction):
            await i.response.defer()
            await interaction.display("closed", keywords={"require_lookup": True}, embed=None)

        await interaction.display(
            "nation_preview",
            keywords={"nation": nation, "require_lookup": True},
            callables={
                "on_accept": accept_override if accept_override else on_accept,
                "on_reject": reject_override if reject_override else on_reject,
            },
            events={ViewEvents.ON_CHECK: ensure_user(interaction.user.id)},
        )

    return confirmation


def cog_find_nation(
    name: str,
) -> Callable[
    [
        Callable[
            Concatenate[commands.Cog, discord.Interaction, UserId, P],
            Coroutine[None, None, None],
        ]
    ],
    Callable[Concatenate[commands.Cog, discord.Interaction, P], Coroutine[None, None, None]],
]:
    def wrapper(
        method: Callable[
            Concatenate[commands.Cog, discord.Interaction, UserId, P],
            Coroutine[None, None, None],
        ],
    ) -> Callable[Concatenate[commands.Cog, discord.Interaction, P], Coroutine[None, None, None]]:
        # signature isn't the same so we need to forge a new signature without name as discord.py inspects it
        @wraps(method)
        @forge.delete(name)
        @forge.copy(method)
        async def class_find_nation(
            self,
            ctx: discord.Interaction,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> None:
            async def closure(nation: UserId) -> None:
                await method(self, ctx, nation, *args, **kwargs)

            await _get_user_target(ctx, closure, self.bot)

        return class_find_nation

    return wrapper


UserIdClosure = Callable[[UserId], Coroutine[None, None, None]]


@dataclass(frozen=True)
class UserIdLookup(EventWithContext[lookup_messages]):
    selector: UserIdClosure

    @event_with_session
    async def on_submit(
        self, session: Session, modal: discord.ui.Modal, interaction: discord.Interaction
    ) -> None:
        user_id = cast(discord.ui.TextInput, modal.children[0]).value
        assert user_id is not None
        await interaction.response.defer()
        if not user_id.isdigit():
            await interaction.response.send_message("User ID is not valid")
        elif not (nation := Nation(UserId(int(user_id)), session)).exists:
            await interaction.response.send_message("User does not have a nation")
        else:
            await _preview_and_return_nation(self.selector)(nation, self.ctx)

    @qalib_event_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
    async def __call__(
        self,
        _: discord.ui.Button,
        interaction: qalib.interaction.QalibInteraction[lookup_messages],
    ) -> None:
        await interaction.rendered_send(
            "get_user_id",
            events={ModalEvents.ON_SUBMIT: self.on_submit},
        )


@dataclass(frozen=True)
class NationNameLookup(EventWithContext[lookup_messages]):
    selector: UserIdClosure

    @event_with_session
    async def on_nation_submit(
        self, session: Session, modal: discord.ui.Modal, interaction: discord.Interaction
    ) -> None:
        nation_name = cast(discord.ui.TextInput, modal.children[0]).value
        assert nation_name is not None
        await interaction.response.defer()
        await _get_user_from_nation_lookup(self.ctx, nation_name, self.selector, session)

    @qalib_event_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
    async def __call__(
        self,
        _: discord.ui.Button,
        interaction: qalib.interaction.QalibInteraction[lookup_messages],
    ) -> None:
        await interaction.rendered_send(
            "nation_select",
            events={ModalEvents.ON_SUBMIT: self.on_nation_submit},
        )


@dataclass(frozen=True)
class UserSelect(EventWithContext[lookup_messages]):
    selector: UserIdClosure

    @qalib_event_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
    @event_with_session
    async def __call__(
        self, session: Session, item: discord.ui.UserSelect, interaction: discord.Interaction
    ) -> None:
        user = item.values[0]
        await interaction.response.defer()
        await _preview_and_return_nation(self.selector)(Nation(UserId(user.id), session), self.ctx)


@qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
async def _get_user_target(
    ctx: QalibInteraction[lookup_messages],
    func: Callable[[UserId], Coroutine[None, None, None]],
    bot: LeagueOfNations,
):
    await ctx.display(
        "target_selection",
        callables={
            "userid": UserIdLookup(bot, ctx, func),
            "user_target": UserSelect(bot, ctx, func),
            "nation": NationNameLookup(bot, ctx, func),
        },
        keywords={"require_lookup": True},
        events={ViewEvents.ON_CHECK: ensure_user(ctx.user.id)},
    )


async def _get_user_from_nation_lookup(
    interaction: QalibInteraction[lookup_messages],
    nation_name: str,
    selector: UserIdClosure,
    session: Session,
):
    nations = Nation.search_for_nations(nation_name, session)

    if not nations:
        await interaction.display(
            "lookup_nation_name_not_found", keywords={"require_lookup": True}, view=None
        )
        return

    async def on_select(item: discord.ui.Select, new_interaction: discord.Interaction):
        nation = Nation(UserId(int(item.values[0])), session)
        await new_interaction.response.defer()

        async def on_reject(_: discord.ui.Button, i: discord.Interaction):
            await i.response.defer()
            await interaction.display(
                "nation_lookup",
                keywords={"nations": nations, "require_lookup": True},
                callables={"on_select": on_select},
                events={ViewEvents.ON_CHECK: ensure_user(interaction.user.id)},
            )

        await _preview_and_return_nation(selector)(nation, interaction, reject_override=on_reject)

    await interaction.display(
        "nation_lookup",
        keywords={"nations": nations, "require_lookup": True},
        callables={"on_select": on_select},
        events={ViewEvents.ON_CHECK: ensure_user(interaction.user.id)},
    )
