import discord
import os
import praw
from discord.ext import commands, tasks
from discord import app_commands
from zoneinfo import ZoneInfo
from datetime import time

class MemeScraper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_SECRET"),
            user_agent=os.getenv('REDDIT_USER_AGENT'),
            check_for_async=False
        )
        
        aedt = ZoneInfo("Australia/Sydney")
        self.meme_time = time(hour=9, minute=0, tzinfo=aedt)
        self.daily_meme.start()

    def cog_unload(self):
        self.daily_meme.cancel()

    @tasks.loop(time=time(hour=9, minute=0, tzinfo=ZoneInfo("Australia/Sydney")))
    async def daily_meme(self):
        meme_channel = self.bot.get_channel(1461252975375810653)
        if not meme_channel: return

        submission = next((s for s in self.reddit.subreddit('leagueofmemes').top(time_filter='day', limit=10)
                           if not s.is_video and not s.is_self and not hasattr(s, 'is_gallery')), None)

        if submission and submission.url:
            embed = discord.Embed(title="Meme of the day", description=submission.title, 
                                  url=f"https://reddit.com{submission.permalink}", color=0xFF5700)
            embed.set_image(url=submission.url)
            embed.set_author(name="r/leagueofmemes", icon_url="https://www.redditstatic.com/desktop2x/img/favicon/apple-icon-57x57.png")
            author = submission.author.name if submission.author else "[deleted]"
            embed.set_footer(text=f"👤 u/{author}")
            await meme_channel.send(embed=embed)
        else:
            await meme_channel.send("No meme today :P")

    @daily_meme.before_loop
    async def before_daily_meme(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(MemeScraper(bot))