import os

import discord
import sqlalchemy.engine
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import create_engine

cogs = "start",


class LeagueOfNations(commands.AutoShardedBot):
    def __init__(self, url: str):
        super().__init__(
            command_prefix="-",
            owner_id=251351879408287744,
            reconnect=True,
            case_insensitive=True,
            intents=discord.Intents.all()
        )
        self._engine = create_engine(url, echo=True)
        self.remove_command('help')
        self.loop.create_task(self.ready())

    @property
    def connection(self) -> sqlalchemy.engine.Connection:
        """Get an active connection to the database, or if one does not exist, then establish a connection

        Returns (sqlalchemy.engine.Connection): An active connection to the database
        """
        return self._engine.connect()

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
    URL = os.getenv("DATABASE_URL")

    assert TOKEN is not None, "MISSING TOKEN IN .env FILE"
    assert URL is not None, "MISSING DATABASE_URL IN .env FILE"

    LeagueOfNations(URL).run(TOKEN)
