import asyncio
import logging
import discord
import urllib3
import os
from discord.ext import commands, tasks
from discord import app_commands
from bs4 import BeautifulSoup
from dataclasses import dataclass
from utils import get_persist, update_persist, get_text_channel

logger = logging.getLogger(__name__)

PATCH_CHANNEL_ID = 1050307222573428756

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
        self._http = urllib3.PoolManager()
        
        self.GAMES = {
            "lol": PatchStrategy(
                "League of Legends",
                "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/",
                "https://www.leagueoflegends.com"
            ),
            "val": PatchStrategy(
                "Valorant",
                "https://playvalorant.com/en-us/news/tags/patch-notes/",
                "https://playvalorant.com"
            ),
            "tft": PatchStrategy(
                "TFT",
                "https://www.leagueoflegends.com/en-au/news/tags/teamfight-tactics-patch-notes/"
            ),
            "riftbd": PatchStrategy(
                "Riftbound",
                "https://riftbound.leagueoflegends.com/en-us/news",
                "https://riftbound.leagueoflegends.com"
            )
        }
        
        self.check_patch.start()

    def cog_unload(self):
        self.check_patch.cancel()

    def fetch_patch(self, strategy: PatchStrategy):
        response = self._http.request("GET", strategy.url, preload_content=True)
        if response.status != 200:
            return None, None

        soup = BeautifulSoup(response.data.decode("utf-8"), self.HTMLPARSER)
        container = soup.find("div", class_=self.RIOT_PATCH_DIVCLASS)
        if not container or not (a := container.find("a")):
            return None, None

        href = a.get("href")
        if not href:
            return None, None
        if href.startswith("/") and strategy.base_url:
            href = strategy.base_url + href
        return a.get("aria-label"), href

    @app_commands.command(name="patchnotes", description="Get latest patch notes for a game")
    @app_commands.choices(game=[
        app_commands.Choice(name="League of Legends", value="lol"),
        app_commands.Choice(name="Valorant", value="val"),
        app_commands.Choice(name="TFT", value="tft"),
        app_commands.Choice(name="Riftbound", value = "riftbd")
    ])
    async def patchnotes(self, interaction: discord.Interaction, game: app_commands.Choice[str]):
        await interaction.response.defer()
        strategy = self.GAMES[game.value]
        title, link = await asyncio.to_thread(self.fetch_patch, strategy)
        
        if not link:
            await interaction.followup.send("Could not fetch patch notes. Ping @zef.")
        else:
            prefix = f"**{strategy.name}** " if strategy.name == "League of Legends" else ""
            await interaction.followup.send(f"{prefix}**{title}**\n{link}")

    @tasks.loop(hours=6)
    async def check_patch(self):
        channel = await get_text_channel(self.bot, PATCH_CHANNEL_ID)
        if not channel:
            logger.warning("check_patch: channel %s not found", PATCH_CHANNEL_ID)
            return
        
        persisted_data = get_persist()
        for key, strategy in self.GAMES.items():
            try:
                title, link = await asyncio.to_thread(self.fetch_patch, strategy)
                last_patch = persisted_data.get(f"last_patch_{key}")

                if title and title != last_patch:
                    msg = (
                        f"**{strategy.name} {title}**\n{link}"
                        if strategy.name == "League of Legends"
                        else f"**{title}**\n{link}"
                    )
                    await channel.send(msg)
                    update_persist(f"last_patch_{key}", title)
                    persisted_data[f"last_patch_{key}"] = title
            except Exception:
                logger.exception("check_patch: failed for game %s", key)

    @check_patch.before_loop
    async def before_check_patch(self):
        await self.bot.wait_until_ready()

    @check_patch.error
    async def check_patch_error(self, error: BaseException):
        logger.exception("check_patch task error", exc_info=error)

async def setup(bot):
    await bot.add_cog(PatchScraper(bot))
