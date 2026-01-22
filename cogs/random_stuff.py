import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
from google import genai
from google.genai import types
import asyncio
import random
import os

class RandomStuff(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.client = genai.Client(api_key=os.getenv("GEMINI_API"))
        self.model_id = "gemini-2.5-flash" 

        prompt_file = Path.cwd() / "data" / "system_prompt.txt"
        with open(prompt_file, "r", encoding="utf-8") as file:
            self.system_prompt = file.read().strip()


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

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author == self.bot.user:
            return

        if self.bot.user.mentioned_in(msg):
            async with msg.channel.typing():
                try:
                    user_input = msg.content.replace(f'<@{self.bot.user.id}>', '').strip()
                    
                    # GEMINI MAGIC
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_prompt
                        ),
                        contents=user_input
                    )
                    # Cull to 2k discord char limit

                    try: 
                        await msg.reply(response.text[:2000])
                    except:
                        await interaction.channel.send("Message being responded to has been deleted")
                except Exception as e:
                    await msg.reply(f"Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(RandomStuff(bot))