import asyncio
import discord
import logging
import os
import requests
import urllib.parse
import random
from discord.ext import commands, tasks
from discord import app_commands

logger = logging.getLogger(__name__)

# riot api timeout
RIOT_TIMEOUT = 5

class RankScraper(commands.Cog):

    # Region mapping for riot API
    # outside of V1 acc api calls needs to be updated with
    # The AMERICAS routing value serves NA, BR, LAN and LAS. 
    # The ASIA routing value serves KR and JP. 
    # The EUROPE routing value serves EUNE, EUW, TR, ME1, and RU.
    # The SEA routing value serves OCE, SG2, TW2 and VN2.
    REGION_MAP = {
        # North & South America
        "na":   {"platform": "na1",  "region": "americas"},
        "br":   {"platform": "br1",  "region": "americas"},
        "lan":  {"platform": "la1",  "region": "americas"},
        "las":  {"platform": "la2",  "region": "americas"},

        # Europe & Middle East
        "euw":  {"platform": "euw1", "region": "europe"},
        "eune": {"platform": "eun1", "region": "europe"},
        "tr":   {"platform": "tr1",  "region": "europe"},
        "ru":   {"platform": "ru",   "region": "europe"},
        "me":   {"platform": "me1",  "region": "europe"},

        # Asia & Oceania
        "kr":   {"platform": "kr",   "region": "asia"},
        "jp":   {"platform": "jp1",  "region": "asia"},
        "oce":  {"platform": "oc1",  "region": "asia"},
        
        # Southeast Asia
        "sg":   {"platform": "sg2",  "region": "asia"},
        "tw":   {"platform": "tw2",  "region": "asia"},
        "vn":   {"platform": "vn2",  "region": "asia"},
    }

    apex_ranks = ["Master", "Grandmaster", "Challenger"]

    def __init__(self, bot):
        self.bot = bot

    async def _riot_get(self, url: str, api_key: str | None) -> requests.Response:
        return await asyncio.to_thread(
            requests.get,
            url,
            headers={"X-Riot-Token": api_key},
            timeout=RIOT_TIMEOUT,
        )

    @staticmethod
    def _split_riot_id(username: str) -> tuple[str, str] | None:
        """Riot IDs are Name#Tag. Returns None if the tag is missing, rather than raising."""
        game_name, _, tag_line = username.partition("#")
        game_name, tag_line = game_name.strip(), tag_line.strip()
        if not game_name or not tag_line:
            return None
        return game_name, tag_line

    # Get PUUID since rito only takes puuid
    async def _resolve_puuid(
        self, region: str, game_name: str, tag_line: str, api_key: str | None
    ) -> str | None:
        acc_url = (
            f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/"
            f"{urllib.parse.quote(game_name)}/{urllib.parse.quote(tag_line)}"
        )
        acc_res = await self._riot_get(acc_url, api_key)
        if acc_res.status_code != 200:
            # 404 is just a typo'd name; 401/403 means the API key has expired.
            logger.info(
                "riot id lookup returned %s for %s#%s", acc_res.status_code, game_name, tag_line
            )
            return None
        return acc_res.json()['puuid']

    # Ik this is terrible and I should of made a service class but it'll get fixed at some point hopefully...
    async def rate_rank(self, rank):
        # Find the cog
        random_stuff_cog = self.bot.get_cog("RandomStuff")
        
        response = await random_stuff_cog.mistral_client.chat.complete_async(
            model="mistral-large-latest",
            messages=[{"role": "user", "content": f"say something snarky while not using quotation marks and at max a sentence or two long about the rank of {rank} in Teamfight Tactics"}],
            temperature=0.85
        )
        return response.choices[0].message.content

    # utilises riot api to pull tft rank
    @app_commands.command(name="tftrank", description="Get a Tacticians's rank and winrate")
    @app_commands.describe(server="The server region (oce, jp, na, etc)", username="Summoner Name#Tag")
    async def tftrank(self, interaction: discord.Interaction, server: str, username: str):
        await interaction.response.defer()

        server_low = server.lower()
        if server_low not in self.REGION_MAP:
            await interaction.followup.send(f"Invalid region provided")
            return

        riot_id = self._split_riot_id(username)
        if riot_id is None:
            await interaction.followup.send("Riot IDs need a tag, like `Faker#KR1`.")
            return
        game_name, tag_line = riot_id

        platform = self.REGION_MAP[server_low]["platform"]
        region = self.REGION_MAP[server_low]["region"]
        api_key = os.getenv("RIOT_TFT_API")

        try:
            puuid = await self._resolve_puuid(region, game_name, tag_line, api_key)
            if puuid is None:
                return await interaction.followup.send(f"Could not find: {username}")

            tft_url = f"https://{platform}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
            tft_res = await self._riot_get(tft_url, api_key)
            tactian_stats = tft_res.json()


            # https://developer.riotgames.com/apis#tft-league-v1/GET_getLeagueEntriesByPUUID
            ranked_tft = next((item for item in tactian_stats if item["queueType"] == "RANKED_TFT"), None)

            if not ranked_tft:
                return await interaction.followup.send(f"**{username}** is currently unranked in TFT.")

            tier = ranked_tft['tier'].capitalize() #otherwise gives rank in all caps
            rank = (" " + ranked_tft['rank']) if tier not in self.apex_ranks else ""
            lp = ranked_tft['leaguePoints']
            wins = ranked_tft['wins']
            losses = ranked_tft['losses']
            wr = round((wins / (wins + losses)) * 100, 1)

            embed = discord.Embed(title=f"{username}'s TFT rank", color=discord.Color.dark_red())
            embed.add_field(name="Current Rank", value=f"{tier}{rank} ({lp} LP)", inline=False)
            embed.add_field(name="Top 4 rate", value=f"{wr}%")

            await interaction.followup.send(embed=embed)
            #1/3 chance to trigger random ai rating
            if random.randint(1, 3) == 1:
                comment = await self.rate_rank(tier)
                await interaction.channel.send(comment)
        except requests.Timeout:
            logger.warning("tftrank: Riot API timed out for %s on %s", username, server_low)
            await interaction.followup.send("Riot's API didn't answer in time, try again in a bit.")
        except Exception:
            # Full traceback lands in data/errors.log - see logging_config.py
            logger.exception("tftrank failed for %s on %s", username, server_low)
            await interaction.followup.send("Something broke fetching that rank. Ping @zef.")

    # utilises seperate api key to pull lol rank since rito made it that way
    @app_commands.command(name="lolrank", description="Get a Summoner's rank and winrate")
    @app_commands.describe(server="The server region (oce, jp, na, etc)", username="Summoner Name#Tag")
    async def lolrank(self, interaction: discord.Interaction, server: str, username: str):
        await interaction.response.defer()

        server_low = server.lower()
        if server_low not in self.REGION_MAP:
            await interaction.followup.send(f"Invalid region provided")
            return

        riot_id = self._split_riot_id(username)
        if riot_id is None:
            await interaction.followup.send("Riot IDs need a tag, like `Faker#KR1`.")
            return
        game_name, tag_line = riot_id

        platform = self.REGION_MAP[server_low]["platform"]
        region = self.REGION_MAP[server_low]["region"]
        api_key = os.getenv("RIOT_LOL_API")

        try:
            puuid = await self._resolve_puuid(region, game_name, tag_line, api_key)
            if puuid is None:
                return await interaction.followup.send(f"Could not find: {username}")

            lolacc_url = f"https://{platform}.api.riotgames.com/lol/league/v4/entries/by-puuid/{puuid}"
            lolacc_res = await self._riot_get(lolacc_url, api_key)
            summoner_stats = lolacc_res.json()

            ranked_stats = next((item for item in summoner_stats if item["queueType"] == "RANKED_SOLO_5x5"), None)

            if not ranked_stats:
                return await interaction.followup.send(f"**{username}** is currently unranked in solo/duo.")

            
            tier = ranked_stats['tier'].capitalize()
            rank = (" " + ranked_stats['rank']) if tier not in self.apex_ranks else ""
            lp = ranked_stats['leaguePoints']
            wins = ranked_stats['wins']
            losses = ranked_stats['losses']
            wr = round((wins / (wins + losses)) * 100, 1)

            embed = discord.Embed(title=f"{username}'s League rank", color=discord.Color.dark_red())
            embed.add_field(name="Current Rank", value=f"{tier}{rank} ({lp} LP)", inline=False)

            if wr < 45:
                emoji = "💀"
            elif wr < 50:
                emoji = "🥀"
            elif wr < 60:
                emoji = "🎉"
            else:
                emoji = "🔥"
            embed.add_field(name="Winrate", value=f"{wr}% {emoji} ({wins}W / {losses}L)")

            await interaction.followup.send(embed=embed)
        except requests.Timeout:
            logger.warning("lolrank: Riot API timed out for %s on %s", username, server_low)
            await interaction.followup.send("Riot's API didn't answer in time, try again in a bit.")
        except Exception:
            # Full traceback lands in data/errors.log - see logging_config.py
            logger.exception("lolrank failed for %s on %s", username, server_low)
            await interaction.followup.send("Something broke fetching that rank. Ping @zef.")

async def setup(bot):
    await bot.add_cog(RankScraper(bot))