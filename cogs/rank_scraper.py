import discord
import urllib3
import os
from discord.ext import commands, tasks
from discord import app_commands
from bs4 import BeautifulSoup

class RankScraper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.HTMLPARSER = "html.parser"

    def clean_rank(self, rank_str):
        parts = rank_str.split()
        match len(parts):
            case 4: return f"{parts[0]} {parts[1]} {parts[3]}"
            case 3: return f"{parts[0]} {parts[2]}"
            case 2: return "Unranked"
            case _: return None

    # Rank scraper from opgg
    def retrieve_rank(self, server, username):
        url = f"https://www.op.gg/summoners/{server.lower()}/{username}"
        http = urllib3.PoolManager()
        response = http.request("GET", url, decode_content=True)
        soup = BeautifulSoup(response.data, self.HTMLPARSER)
        meta_tag = soup.find("meta", {"property": "og:description"})
        
        if not meta_tag: return None, None

        parts = [p.strip() for p in meta_tag.get("content", "").split("/")]
        # Example content:
        # "DaHoodDuck#Quack / Platinum 4 0LP / 84Win 81Lose Win rate 51% / Brand ..."
        rank_info = self.clean_rank(parts[1] if len(parts) > 1 else "Unknown")
        overall_wr = parts[2] if len(parts) > 2 else "Unknown"
        return rank_info, overall_wr

    @app_commands.command(name="rank", description="Get a summoner's rank and winrate")
    @app_commands.describe(server="The server region", username="Summoner Name#Tag")
    async def rank(self, interaction: discord.Interaction, server: str, username: str):
        await interaction.response.defer()
        rankinfo, overall_wr = self.retrieve_rank(server, username.replace("#", "-"))

        if rankinfo is None:
            await interaction.followup.send(f"Could not find rank info for **{username}** on {server.upper()}.")
        elif rankinfo == "Unranked":
            await interaction.followup.send(f"**{username}** is Unranked.")
        else:
            parts = overall_wr.split("Win rate")
            winrate_num = int(parts[1].strip().rstrip("%"))
            emoji = "🥀" if winrate_num < 50 else "🎉"
            embed = discord.Embed(
                title=f"{username} ({server.upper()})",
                description=f"{rankinfo} \n Win rate {parts[1].strip()} {emoji} \n {parts[0].strip()}",
                color=discord.Color.dark_red()
            )
            await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(RankScraper(bot))