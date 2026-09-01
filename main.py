import logging
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

from logging_config import setup_logging

load_dotenv()
setup_logging()

logger = logging.getLogger(__name__)

TOKEN = os.getenv("DISCORD_TOKEN")
ADMIN_GUILD_ID = int(os.getenv("ADMIN_GUILD_ID"))

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True

class RiotSocBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='>',
            intents=intents,
            help_command=None
        )

    async def setup_hook(self):
        # Load cogs
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                except Exception:
                    # One broken cog shouldn't take the whole bot down silently.
                    logger.exception("failed to load cog %s", filename)

        await self.tree.sync()
        await self.tree.sync(guild=discord.Object(id=ADMIN_GUILD_ID))

        logger.info("Synced slash commands for %s globally and for admin server", self.user)

bot = RiotSocBot()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.CustomActivity(name='/help for commands'))
    logger.info("%s is online!", bot.user)

if __name__ == "__main__":
    # log_handler=None tells discord.py not to install its own handler - setup_logging()
    # already owns the root logger, and discord.* propagates into it.
    try:
        bot.run(TOKEN, log_handler=None)
    except Exception:
        logger.exception("bot exited with an unhandled exception")
        raise
