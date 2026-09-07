import logging
import discord
from discord.ext import commands
from discord import app_commands
import os

from utils import get_text_channel

logger = logging.getLogger(__name__)

class General(commands.Cog):
    ADMIN_GUILD_ID = int(os.getenv("ADMIN_GUILD_ID"))

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        guild_id = os.getenv("RIOTSOC_GUILD_ID")
        if not guild_id or member.guild.id != int(guild_id):
            return

        rules_channel = "https://discord.com/channels/312743332579377152/1050317772703416381"
        message = (
            f"Welcome {member.name} to RiotSoc!\n"
            f"Please read our rules at {rules_channel} to get started. "
            "If you need help for anything at all, feel free to message an exec or ping a subcomm!"
        )

        try:
            await member.send(message)
        except discord.Forbidden:
            pass  # in case DMs are closed

    # speaking as the bot is only possible in the admin guild
    @app_commands.guilds(discord.Object(id=ADMIN_GUILD_ID))
    @app_commands.command(name="say", description="Send a message as the bot in a given channel")
    @app_commands.describe(
        channel_id="ID of the channel to send the message in",
        message="What the bot should say (\\n for line breaks)"
    )
    async def say(self, interaction: discord.Interaction, channel_id: str, message: str):
        # str param because snowflakes overflow the slash command integer range
        try:
            target_id = int(channel_id.strip())
        except ValueError:
            await interaction.response.send_message(f"{channel_id} isn't a valid channel ID.", ephemeral=True)
            return

        channel = await get_text_channel(self.bot, target_id)
        if channel is None:
            await interaction.response.send_message(f"Couldn't find a channel I can post in with ID {target_id}.", ephemeral=True)
            return

        content = message.replace("\\n", "\n")

        try:
            sent = await channel.send(content[:2000])
        except discord.HTTPException as e:
            logger.exception("say: failed to send bot as message to channel %s", target_id)
            await interaction.response.send_message(f"Failed to send: {e}", ephemeral=True)
            return

        logger.info("say: user %s sent a message to channel %s", interaction.user.id, target_id)
        await interaction.response.send_message(f"Sent: {sent.jump_url}", ephemeral=True)

    @app_commands.command(name="help", description="Displays all available bot commands")
    async def help_command(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="RiotSoc Bot", 
            description="Here is a list of all available slash commands",
            color=discord.Color.dark_red()
        )
        
        for cmd in self.bot.tree.get_commands():
            embed.add_field(name=f"/{cmd.name}", value=cmd.description or "N/A", inline=False)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(General(bot))