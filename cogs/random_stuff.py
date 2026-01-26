import discord
from discord.ext import commands
from discord import app_commands
from pathlib import Path
from google import genai
from google.genai import types
from mistralai import Mistral
from owoify.owoify import owoify, Owoness
import asyncio
import random
import os

# Let it recognise people
# blame
# clanker

class RandomStuff(commands.Cog):
    ADMIN_GUILD_ID = 1413504927996706909
    def __init__(self, bot):
        self.bot = bot
        # self.client = genai.Client(api_key=os.getenv("GEMINI_API"))
        # self.model_id = "gemini-2.5-flash" 
        self.mistral_client = Mistral(api_key=os.getenv("MISTRAL_API"))
        self.model_id = "mistral-medium-latest"

        self.owolvl="none"

        prompt_file = Path.cwd() / "data" / "system_prompt.txt"
        with open(prompt_file, "r", encoding="utf-8") as file:
            self.system_prompt = file.read().strip()

    # setting uwu level only possible in admin guild
    @app_commands.guilds(discord.Object(id=ADMIN_GUILD_ID))
    @app_commands.command(name="uwulvl")
    @app_commands.choices(mode=[
        *[app_commands.Choice(name=m.name.lower(), value=str(m.value)) for m in Owoness],
        app_commands.Choice(name="none", value="none") 
    ])
    async def uwulvl(self, interaction: discord.Interaction, mode: app_commands.Choice[str]):
        # Store the value
        self.owolvl = mode.value 
        
        if mode.value == "none":
            await interaction.response.send_message("Uwu filtering disabled.", ephemeral=True)
        else:
            await interaction.response.send_message(f"Set lvl to {mode.name}", ephemeral=True)

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

    # Goes back up chain of replies to add to context
    async def get_context(self, msg):
        history = []
        curr_msg = msg

        # arbritrary limit
        for _ in range(6):
            if not curr_msg.reference:
                break
            
            try:
                # Get the parent msg object (resolve from cache or fetch from API)
                if curr_msg.reference.cached_message:
                    parent_msg = curr_msg.reference.cached_message
                else:
                    parent_msg = await msg.channel.fetch_message(curr_msg.reference.message_id)

                role = "assistant" if parent_msg.author == self.bot.user else "user"
                parent_input = parent_msg.content.replace(f'<@{self.bot.user.id}>', 'RiotSocBot').strip()
                if role == "user": 
                    parent_input = parent_msg.author.display_name + ": " + parent_input

                history.insert(0, {"role": role, "content": parent_input})

                curr_msg = parent_msg
            except Exception as e:
                # in case chain is broken
                await msg.channel.send(f"error: {str(e)}")
                break
        return history
                

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author == self.bot.user:
            return

        if "clanker" in msg.content.lower():
            violator = msg.author.display_name
            async with msg.channel.typing():
                try:
                    response = await self.mistral_client.chat.complete_async(
                        model="mistral-small-latest",
                        messages=[
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": violator + " called you a 'clanker with in the following message: " + msg.content}
                        ],
                        temperature=0.95
                    )
                    response_text = response.choices[0].message.content
                    await msg.channel.send(response_text)
                except Exception as e:
                    await msg.reply(f"Error: {str(e)}")


        if self.bot.user.mentioned_in(msg):
            async with msg.channel.typing():
                try:
                    user_input = msg.content.replace(f'<@{self.bot.user.id}>', 'RiotSocBot').strip()
                    
                    """ # GEMINI MAGIC
                    response = self.client.models.generate_content(
                        model=self.model_id,
                        config=types.GenerateContentConfig(
                            system_instruction=self.system_prompt
                        ),
                        contents=user_input
                    ) """

                    messages = [
                        {"role": "system", "content": self.system_prompt}
                    ]

                    # handle reply chain with context
                    if msg.reference:
                        context_history = await self.get_context(msg)
                        messages.extend(context_history)

                    # add current msg
                    msg_author = msg.author.display_name
                    messages.append({"role": "user", "content": msg_author + ": " + user_input})
                
                    # response is in json.
                    response = await self.mistral_client.chat.complete_async(
                        model=self.model_id,
                        messages=messages,
                        temperature=0.7,
                        frequency_penalty=0.1,
                        random_seed=None
                    )
                    response_text = response.choices[0].message.content

                    if self.owolvl != "none":
                        response_text = owoify(response_text, Owoness(int(self.owolvl)))

                    # Cull to 2k discord char limit
                    try: 
                        await msg.reply(response_text[:2000])
                    except:
                        await msg.channel.send("Message being responded to has been deleted")
                except Exception as e:
                    await msg.reply(f"Error: {str(e)}")

async def setup(bot):
    await bot.add_cog(RandomStuff(bot))