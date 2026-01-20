import discord
from discord.ext import commands
from discord import app_commands
import random

class Fun(commands.Cog):
    def __init__(self, bot):
        self.bot = bot


    @app_commands.command(name="blame", description="Blame a random squid for everything")
    async def blame(self, interaction: discord.Interaction):
        squids = [467683010213314560, 443721622965452810]
        chosen_id = random.choice(squids)
        
        blame_messages = [
            "is responsible for this chaos!",
            "did it again, blame them!",
            "somehow caused this mess!",
            "is the culprit here!",
            "you know who did it...",
            "ofc this guy would be the one who messed up",
            "totally the mastermind behind this disaster!",
            "should probably be held accountable...",
            "yep, it’s them. no questions.",
            "went above and beyond to make this disaster!",
            "clearly the reason everything is broken!",
            "didn’t even try to hide it this time!",
            "the legend behind today’s catastrophe!",
            "messed up again",
            "definitely the one to blame, as usual!"
        ]

        
        await interaction.response.send_message("Consider it done.", ephemeral=True)
        await interaction.channel.send(f"<@{chosen_id}> {random.choice(blame_messages)}")

async def setup(bot):
    await bot.add_cog(Fun(bot))