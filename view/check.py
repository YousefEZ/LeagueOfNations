import discord.ui
from qalib.translators.view import CheckEvent


def ensure_user(user: int) -> CheckEvent:
    async def check(_: discord.ui.View, interaction: discord.Interaction) -> bool:
        return interaction.user.id == user

    return check
