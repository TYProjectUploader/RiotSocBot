import discord
import urllib3
import json
import os
from discord.ext import commands, tasks
from discord import app_commands
from bs4 import BeautifulSoup
from dataclasses import dataclass
from utils import get_persist, update_persist

@dataclass
class PatchStrategy:
    name: str
    url: str
    base_url: str = ""

class PatchScraper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.HTMLPARSER = "html.parser"
        self.RIOT_PATCH_DIVCLASS = "sc-4d29e6fd-0 hzTXxn"
        
        self.GAMES = {
            "lol": PatchStrategy("League of Legends", "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/", "https://www.leagueoflegends.com"),
            "val": PatchStrategy("Valorant", "https://playvalorant.com/en-us/news/tags/patch-notes/", "https://playvalorant.com"),
            "tft": PatchStrategy("TFT", "https://www.leagueoflegends.com/en-au/news/tags/teamfight-tactics-patch-notes/")
        }
        
        self.check_patch.start()

    def cog_unload(self):
        self.check_patch.cancel()

    def fetch_patch(self, strategy: PatchStrategy):
        http = urllib3.PoolManager()
        response = http.request("GET", strategy.url, preload_content=True)
        if response.status != 200: return None, None

        soup = BeautifulSoup(response.data.decode("utf-8"), self.HTMLPARSER)
        container = soup.find("div", class_=self.RIOT_PATCH_DIVCLASS)
        if not container or not (a := container.find("a")): return None, None

        href = a["href"]
        if href.startswith("/") and strategy.base_url:
            href = strategy.base_url + href
        return a.get("aria-label"), href

    @app_commands.command(name="patchnotes", description="Get latest patch notes for a game")
    @app_commands.choices(game=[
        app_commands.Choice(name="League of Legends", value="lol"),
        app_commands.Choice(name="Valorant", value="val"),
        app_commands.Choice(name="TFT", value="tft")
    ])
    async def patchnotes(self, interaction: discord.Interaction, game: app_commands.Choice[str]):
        await interaction.response.defer()
        strategy = self.GAMES[game.value]
        title, link = self.fetch_patch(strategy)
        
        if not link:
            await interaction.followup.send("Could not fetch patch notes. Ping @zef.")
        else:
            prefix = f"**{strategy.name}** " if strategy.name == "League of Legends" else ""
            await interaction.followup.send(f"{prefix}**{title}**\n{link}")

    # Patch auto checker
    @tasks.loop(hours=6)
    async def check_patch(self):
        channel = self.bot.get_channel(1461268298665693247)
        if not channel: return
        
        persisted_data = get_persist()
        for key, strategy in self.GAMES.items():
            title, link = self.fetch_patch(strategy)
            last_patch = persisted_data.get(f"last_patch_{key}")

            if title and title != last_patch:
                msg = f"**{strategy.name} {title}**\n{link}" if strategy.name == "League of Legends" else f"**{title}**\n{link}"
                await channel.send(msg)
                update_persist(f"last_patch_{key}", title)

    @check_patch.before_loop
    async def before_check_patch(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(PatchScraper(bot))