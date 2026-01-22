import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
import asyncio
import random

class RandomStuff(commands.Cog):
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

    @app_commands.command(name="bad-apple", description="Why wouldn't this be a feature?")
    async def bad_apple(self, interaction: discord.Interaction):
        file_path = Path.cwd() / "data" / "badapplegifs.txt"

        with open(file_path, "r") as file:
            urls = file.read().splitlines()

        await interaction.response.send_message(urls[0])

        try:
            for url in urls[1:]:
                await asyncio.sleep(9.9)
                await interaction.edit_original_response(content=url)
        except discord.NotFound:
            # In case message is deleted
            await interaction.channel.send("Who tf interrupted my bad apple?")
            return

        await interaction.delete_original_response()

async def setup(bot):
    await bot.add_cog(RandomStuff(bot))