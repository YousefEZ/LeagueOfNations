import os

import discord
import sqlalchemy.engine
from discord.ext import commands
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

import host.base_models
from host.nation import Nation
from host.base_types import UserId

cogs = "start", "economy"
connect_to_db = False


class LeagueOfNations(commands.AutoShardedBot):
    def __init__(self, url: str):
        super().__init__(
            command_prefix="-",
            owner_id=251351879408287744,
            reconnect=True,
            case_insensitive=True,
            intents=discord.Intents.all()
        )
        self.engine: Engine = create_engine(url, echo=True)
        host.base_models.Base.metadata.create_all(self.engine)
        self.remove_command('help')

    async def setup_hook(self) -> None:
        self.loop.create_task(self.ready())

    def get_nation(self, user_id: int) -> Nation:
        """Get the nation of the user with that user identifier

        Args:
            user_id (UserId): The ID of the user to get

        Returns (discord.User): The user
        """
        return Nation(UserId(user_id), self.engine)

    @commands.command()
    async def sync(self, ctx):
        await ctx.bot.tree.sync(guid=ctx.guild)
        await ctx.send("Synced")

    @property
    def connection(self) -> sqlalchemy.engine.Connection:
        """Get an active connection to the database, or if one does not exist, then establish a connection

        Returns (sqlalchemy.engine.Connection): An active connection to the database
        """
        return self.engine.connect()

    async def ready(self):
        await self.wait_until_ready()

        try:
            for cog in cogs:
                await self.load_extension(f"cogs.{cog}")
        except Exception as e:
            print('*[CLIENT][LOADING_EXTENSION][STATUS] ERROR ', e)
        else:
            print('*[CLIENT][LOADING_EXTENSION][STATUS] SUCCESS')

        await self.tree.sync()


if __name__ == "__main__":
    load_dotenv()

    TOKEN = os.getenv("DISCORD_TOKEN")
    URL = os.getenv("DATABASE_URL")
    assert TOKEN is not None, "MISSING TOKEN IN .env FILE"
    assert URL is not None, "MISSING DATABASE_URL IN .env FILE"

    LeagueOfNations(URL).run(token=TOKEN)
