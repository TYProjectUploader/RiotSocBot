import discord
from discord.ext import commands
from discord import app_commands

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        rules_channel = "https://discord.com/channels/312743332579377152/1050317772703416381"
        await member.send(f"Welcome {member.name} to RiotSoc!\nPlease read our rules at {rules_channel}")

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