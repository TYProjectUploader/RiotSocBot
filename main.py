import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

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
                await self.load_extension(f'cogs.{filename[:-3]}')
        
        # Sync test server
        """ guild_obj = discord.Object(id=1413504927996706909)
        await self.tree.sync(guild=guild_obj) """
        await self.tree.sync()
        print(f"Synced slash commands for {self.user}")

bot = RiotSocBot()

@bot.event
async def on_ready():
    await bot.change_presence(activity=discord.CustomActivity(name='/help for commands'))
    print(f'{bot.user} is online!')

bot.run(TOKEN)