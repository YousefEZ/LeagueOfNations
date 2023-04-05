import os

import discord
from discord.ext import commands
from dotenv import load_dotenv

cogs = tuple()

class LeagueOfNations(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix="-",
            owner_id=251351879408287744,
            reconnect=True,
            case_insensitive=True,
            intents=discord.Intents.all()
        )
        self.remove_command('help')
        self.loop.create_task(self.ready())

    async def ready(self):
        await self.wait_until_ready()

        try:
            for cog in cogs:
                await self.load_extension(f"cogs.{cog}")
        except Exception as e:
            print('*[CLIENT][LOADING_EXTENSION][STATUS] ERROR ', e)
        else:
            print('*[CLIENT][LOADING_EXTENSION][STATUS] SUCCESS')


if __name__ == "__main__":
    load_dotenv()
    TOKEN = os.getenv("DISCORD_TOKEN")
    assert TOKEN is not None, "MISSING TOKEN IN .env FILE"
    LeagueOfNations().run(TOKEN)
