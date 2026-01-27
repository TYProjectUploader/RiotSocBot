import discord
import urllib3
import os
import requests
import urllib.parse
from discord.ext import commands, tasks
from discord import app_commands
from bs4 import BeautifulSoup

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

    def __init__(self, bot):
        self.bot = bot
        self.HTMLPARSER = "html.parser"

    def clean_lolrank(self, rank_str):
        parts = rank_str.split()
        match len(parts):
            case 4: return f"{parts[0]} {parts[1]} {parts[3]}"
            case 3: return f"{parts[0]} {parts[2]}"
            case 2: return "Unranked"
            case _: return None

    # Rank scraper from opgg
    def retrieve_lolrank(self, server, username):
        url = f"https://www.op.gg/summoners/{server.lower()}/{username}"
        http = urllib3.PoolManager()
        response = http.request("GET", url, decode_content=True)
        soup = BeautifulSoup(response.data, self.HTMLPARSER)
        meta_tag = soup.find("meta", {"property": "og:description"})
        
        if not meta_tag: return None, None

        parts = [p.strip() for p in meta_tag.get("content", "").split("/")]
        # Example content:
        # "DaHoodDuck#Quack / Platinum 4 0LP / 84Win 81Lose Win rate 51% / Brand ..."
        rank_info = self.clean_lolrank(parts[1] if len(parts) > 1 else "Unknown")
        overall_wr = parts[2] if len(parts) > 2 else "Unknown"
        return rank_info, overall_wr

    @app_commands.command(name="lolrank", description="Get a summoner's rank and winrate")
    @app_commands.describe(server="The server region (oce, jp, na, etc)", username="Summoner Name#Tag")
    async def lolrank(self, interaction: discord.Interaction, server: str, username: str):
        await interaction.response.defer()
        rankinfo, overall_wr = self.retrieve_lolrank(server, username.replace("#", "-"))

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

    # utilises riot api to pull tft rank
    @app_commands.command(name="tftrank", description="Get a Tacticians's rank and winrate")
    @app_commands.describe(server="The server region (oce, jp, na, etc)", username="Summoner Name#Tag")
    async def tftrank(self, interaction: discord.Interaction, server: str, username: str):
        await interaction.response.defer()

        server_low = server.lower()
        if server_low not in self.REGION_MAP:
            await interaction.followup.send(f"Invalid region provided")
            return

        game_name, tag_line = username.split("#", 1)
        platform = self.REGION_MAP[server_low]["platform"]
        region = self.REGION_MAP[server_low]["region"]

        headers = {"X-Riot-Token": os.getenv("RIOT_TFT_API")}

        try:
            # Get PUUID since rito only takes puuid
            acc_url = f"https://{region}.api.riotgames.com/riot/account/v1/accounts/by-riot-id/{urllib.parse.quote(game_name)}/{tag_line}"
            acc_res = requests.get(acc_url, headers=headers)
            if acc_res.status_code != 200:
                return await interaction.followup.send(f"Could not find: {username}")
            
            puuid = acc_res.json()['puuid']

            tft_url = f"https://{platform}.api.riotgames.com/tft/league/v1/by-puuid/{puuid}"
            tft_res = requests.get(tft_url, headers=headers)
            tactian_stats = tft_res.json()


            # https://developer.riotgames.com/apis#tft-league-v1/GET_getLeagueEntriesByPUUID
            ranked_tft = next((item for item in tactian_stats if item["queueType"] == "RANKED_TFT"), None)

            if not ranked_tft:
                return await interaction.followup.send(f"**{username}** is Unranked in TFT.")

            tier = ranked_tft['tier'].capitalize() #otherwise gives rank in all caps
            rank = ranked_tft['rank']
            lp = ranked_tft['leaguePoints']
            wins = ranked_tft['wins']
            losses = ranked_tft['losses']
            wr = round((wins / (wins + losses)) * 100, 1)

            embed = discord.Embed(title=f"{username}'s TFT rank", color=discord.Color.dark_red())
            embed.add_field(name="Current Rank", value=f"{tier} {rank} ({lp} LP)")
            embed.add_field(name="Top 4 rate", value=f"{wr}% ({wins}W / {losses}L)")

            await interaction.followup.send(embed=embed)
        except Exception as e:
            await interaction.followup.send(f"An error occurred: {str(e)}")

async def setup(bot):
    await bot.add_cog(RankScraper(bot))