import asyncio
import logging
import discord
import os
import praw
from discord.ext import commands, tasks
from zoneinfo import ZoneInfo
from datetime import time

from utils import get_text_channel

logger = logging.getLogger(__name__)

MEME_CHANNEL_ID = 1050306304083775558

class MemeScraper(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        
        self.reddit = praw.Reddit(
            client_id=os.getenv("REDDIT_CLIENT_ID"),
            client_secret=os.getenv("REDDIT_SECRET"),
            user_agent=os.getenv('REDDIT_USER_AGENT'),
            check_for_async=False
        )
        
        self.daily_meme.start()

    def cog_unload(self):
        self.daily_meme.cancel()

    def _pick_submission(self):
        return next(
            (
                s for s in self.reddit.subreddit('leagueofmemes').top(time_filter='day', limit=10)
                if not s.is_video and not s.is_self and not getattr(s, 'is_gallery', False)
            ),
            None,
        )

    @tasks.loop(time=time(hour=9, minute=0, tzinfo=ZoneInfo("Australia/Sydney")))
    async def daily_meme(self):
        meme_channel = await get_text_channel(self.bot, MEME_CHANNEL_ID)
        if not meme_channel:
            logger.warning("daily_meme: channel %s not found", MEME_CHANNEL_ID)
            return

        try:
            submission = await asyncio.to_thread(self._pick_submission)
        except Exception:
            logger.exception("daily_meme: failed to fetch from Reddit")
            await meme_channel.send("No meme today :P (Reddit fetch failed)")
            return

        if submission and submission.url:
            embed = discord.Embed(
                title="Meme of the day",
                description=submission.title,
                url=f"https://reddit.com{submission.permalink}",
                color=0xFF5700,
            )
            embed.set_image(url=submission.url)
            embed.set_author(
                name="r/leagueofmemes",
                icon_url="https://www.redditstatic.com/desktop2x/img/favicon/apple-icon-57x57.png",
            )
            author = submission.author.name if submission.author else "[deleted]"
            embed.set_footer(text=f"👤 u/{author}")
            await meme_channel.send(embed=embed)
        else:
            await meme_channel.send("No meme today :P")

    @daily_meme.before_loop
    async def before_daily_meme(self):
        await self.bot.wait_until_ready()

    @daily_meme.error
    async def daily_meme_error(self, error: BaseException):
        logger.exception("daily_meme task error", exc_info=error)

async def setup(bot):
    await bot.add_cog(MemeScraper(bot))
