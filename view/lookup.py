from functools import partial, wraps
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
from lon import interaction_morph
from view.check import ensure_user
from view.cogs.custom_jinja2 import ENVIRONMENT

__all__ = (
    "cog_find_nation",
    "find_nation",
)


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
    func: Callable[
        Concatenate[discord.Interaction, Session, Nation, P], Coroutine[None, None, None]
    ],
    session: Session,
    *args: P.args,
    **kwargs: P.kwargs,
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
                await func(interaction, session, nation, *args, **kwargs)
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
            Concatenate[commands.Cog, discord.Interaction, Session, Nation, P],
            Coroutine[None, None, None],
        ]
    ],
    Callable[
        Concatenate[commands.Cog, discord.Interaction, Session, P], Coroutine[None, None, None]
    ],
]:
    def wrapper(
        method: Callable[
            Concatenate[commands.Cog, discord.Interaction, Session, Nation, P],
            Coroutine[None, None, None],
        ],
    ) -> Callable[
        Concatenate[commands.Cog, discord.Interaction, Session, P], Coroutine[None, None, None]
    ]:
        # signature isn't the same so we need to forge a new signature without name as discord.py inspects it
        @wraps(method)
        @forge.delete(name)
        @forge.copy(method)
        async def class_find_nation(
            self,
            ctx: discord.Interaction,
            session: Session,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> None:
            await _get_user_target(ctx, partial(method, self), session, *args, **kwargs)

        return class_find_nation

    return wrapper


def find_nation(
    name: str,
) -> Callable[
    [
        Callable[
            Concatenate[discord.Interaction, Session, Nation, P],
            Coroutine[None, None, None],
        ]
    ],
    Callable[Concatenate[discord.Interaction, Session, P], Coroutine[None, None, None]],
]:
    def wrapper(
        func: Callable[
            Concatenate[discord.Interaction, Session, Nation, P],
            Coroutine[None, None, None],
        ],
    ) -> Callable[Concatenate[discord.Interaction, Session, P], Coroutine[None, None, None]]:
        @forge.delete(name)
        @forge.copy(func)
        async def find_nation_wrapper(
            ctx: discord.Interaction,
            session: Session,
            *args: P.args,
            **kwargs: P.kwargs,
        ) -> None:
            await _get_user_target(ctx, func, session, *args, **kwargs)

        return find_nation_wrapper

    return wrapper


@qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
async def _get_user_target(
    ctx: QalibInteraction[lookup_messages],
    func: Callable[
        Concatenate[discord.Interaction, Session, Nation, P], Coroutine[None, None, None]
    ],
    session: Session,
    *args: P.args,
    **kwargs: P.kwargs,
):
    selector = _preview_and_return_nation(func, session, *args, **kwargs)

    async def on_id_submit(modal: discord.ui.Modal, interaction: discord.Interaction) -> None:
        user_id = cast(discord.ui.TextInput, modal.children[0]).value
        assert user_id is not None
        await interaction.response.defer()
        if not user_id.isdigit():
            await interaction.response.send_message("User ID is not valid")
        elif not (nation := Nation(UserId(int(user_id)), session)).exists:
            await interaction.response.send_message("User does not have a nation")
        else:
            await selector(nation, ctx)

    async def on_nation_submit(modal, interaction: discord.Interaction) -> None:
        nation_name = cast(discord.ui.TextInput, modal.children[0]).value
        assert nation_name is not None
        await interaction.response.defer()
        await _get_user_from_nation_lookup(ctx, nation_name, func, session, *args, **kwargs)

    @interaction_morph
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
    async def open_id_modal(
        interaction: qalib.interaction.QalibInteraction[lookup_messages],
    ) -> None:
        await interaction.rendered_send(
            "get_user_id",
            events={ModalEvents.ON_SUBMIT: on_id_submit},
            keywords={"require_lookup": True},
        )

    @interaction_morph
    @qalib.qalib_interaction(Jinja2(ENVIRONMENT), "templates/lookup.xml")
    async def open_nation_modal(
        interaction: qalib.interaction.QalibInteraction[lookup_messages],
    ) -> None:
        await interaction.rendered_send(
            "nation_select",
            events={ModalEvents.ON_SUBMIT: on_nation_submit},
            keywords={"require_lookup": True},
        )

    async def on_user_select(
        item: discord.ui.UserSelect,
        i: discord.Interaction,
    ) -> None:
        user = item.values[0]
        await i.response.defer()
        await selector(Nation(UserId(user.id), session), ctx)

    await ctx.display(
        "target_selection",
        callables={
            "userid": open_id_modal,
            "user_target": on_user_select,
            "nation": open_nation_modal,
        },
        keywords={"require_lookup": True},
        events={ViewEvents.ON_CHECK: ensure_user(ctx.user.id)},
    )


async def _get_user_from_nation_lookup(
    interaction: QalibInteraction[lookup_messages],
    nation_name: str,
    func: Callable[
        Concatenate[discord.Interaction, Session, Nation, P], Coroutine[None, None, None]
    ],
    session: Session,
    *args: P.args,
    **kwargs: P.kwargs,
):
    nations = Nation.search_for_nations(nation_name, session)

    selection = _preview_and_return_nation(func, session, *args, **kwargs)
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

        await selection(nation, interaction, reject_override=on_reject)

    await interaction.display(
        "nation_lookup",
        keywords={"nations": nations, "require_lookup": True},
        callables={"on_select": on_select},
        events={ViewEvents.ON_CHECK: ensure_user(interaction.user.id)},
    )
