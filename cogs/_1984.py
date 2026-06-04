import discord
import logging
import random
import re
import os
from discord.ext import commands
from datetime import datetime, timedelta, timezone
from owoify import owoify
from owoify.owoify import Owoness

logger = logging.getLogger(__name__)

class _1984(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.uncensored_offenses = {}
        
        self.CENSORED_WORDS = {
            r"\bjob": r"j\*b",
            r"\boccupation": r"*cc\*p\*t\*\*n", 
            r"\bemployment": r"\*mpl\*ym\*nt",
            r"\bemployed": r"\*mpl\*y\*d", 
            r"\bwork": r"w\*rk",
            r"\bhire": r"h\*r\*",
            r"\binterview": r"\*nt\*rv\*\*w", 
            r"\bintern(?!et|al|ation|ity)": r"\*nt\*rn",
            r"\bcareer": r"c\*r\*\*r",
            r"\bresume": r"r\*s\*m\*", 
            r"\bemployee": r"\*mpl\*y\*\*", 
            r"\bstaff": r"st\*ff",
            r"\bwage": r"w\*g\*",
            r"\bsalary": r"s\*l\*ry"
        }
        
        self.censor_pattern = re.compile(
            r"|".join(self.CENSORED_WORDS.keys()), 
            re.IGNORECASE
        )

        self.WHITELIST_ROLES = [
            int(v) for v in (
                os.getenv("EXEC_ROLE_ID"),
                os.getenv("DIRECTOR_ROLE_ID"),
                os.getenv("RIOT_ROLE_ID"),
            ) if v
        ]
        self.WHITELIST_CHANNELS = {123456789012345678}
        self.WHITELIST_GUILDS = {1464920295881314304}

        self.WHITE_LIST_CHANNELS = [
            312748799799984130,
            1343524032158367744,
            1050317772703416381
        ]

    def censor_message(self, content):
        censored = content
        for word, replacement in self.CENSORED_WORDS.items():
            censored = re.sub(word, replacement, censored, flags=re.IGNORECASE)
        return censored

    async def _get_member(self, guild: discord.Guild, author: discord.abc.User) -> discord.Member | None:
        if isinstance(author, discord.Member):
            return author
        member = guild.get_member(author.id)
        if member is not None:
            return member
        try:
            return await guild.fetch_member(author.id)
        except discord.NotFound:
            return None

    def _has_whitelist_role(self, member: discord.Member | None) -> bool:
        if member is None:
            return False
        return any(role.id in self.WHITELIST_ROLES for role in member.roles)

    async def _owoify_edit_prank(self, channel: discord.TextChannel, message: discord.Message, content: str):
        if message.author.bot or random.randint(1, 3) != 1:
            return

        owoified = owoify(content, Owoness.Uwu)[:2000]
        files = [await attachment.to_file() for attachment in message.attachments]

        try:
            webhook = await channel.create_webhook(name="RiotSocBot")
            try:
                await webhook.send(
                    owoified,
                    username=message.author.display_name,
                    avatar_url=message.author.display_avatar.url,
                    files=files or None,
                )
            finally:
                await webhook.delete()
            await message.delete()
        except discord.Forbidden:
            await channel.send(f"{message.author.mention} {owoified}", files=files or None)
            await message.delete()
        except discord.HTTPException:
            logger.exception("owoify edit prank failed for message %s", message.id)

    async def _censor_violation(self, channel, message: discord.Message, followup: str):
        censored_text = self.censor_message(message.content)
        files = [await attachment.to_file() for attachment in message.attachments]
        await channel.send(
            content=f"I've censored {message.author.mention}'s text: {censored_text}",
            files=files or None,
        )
        await channel.send(followup)
        await channel.send(files=[discord.File('neurosig.jpg')], delete_after=5)
        await message.delete()

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.channel_id in self.WHITE_LIST_CHANNELS:
            return
        if payload.channel_id in self.WHITELIST_CHANNELS:
            return
        if payload.guild_id in self.WHITELIST_GUILDS:
            return
        if not payload.guild_id:
            return

        data = payload.data
        if not data:
            return
        content = data.get('content', '')
        if not content:
            return

        try:
            guild = self.bot.get_guild(payload.guild_id)
            if not guild:
                return

            channel = self.bot.get_channel(payload.channel_id)
            if channel is None:
                channel = await self.bot.fetch_channel(payload.channel_id)
            if not isinstance(channel, discord.TextChannel):
                return

            message = await channel.fetch_message(payload.message_id)
            member = await self._get_member(guild, message.author)
            if self._has_whitelist_role(member):
                return

            if message.author.bot:
                return

            if self.censor_pattern.search(content.lower()):
                await self._censor_violation(
                    channel,
                    message,
                    "Really? You thought editing your message would let you bypass me?",
                )
                return

            await self._owoify_edit_prank(channel, message, content)
        except Exception:
            logger.exception("on_raw_message_edit failed for message %s", payload.message_id)

    @commands.Cog.listener()
    async def on_message(self, msg: discord.Message):
        if msg.channel.id in self.WHITE_LIST_CHANNELS:
            return
        if msg.author.bot:
            return
        if not msg.guild:
            return

        member = await self._get_member(msg.guild, msg.author)
        if self._has_whitelist_role(member):
            return
        
        if msg.guild.id in self.WHITELIST_GUILDS:
            return

        if msg.channel.id in self.WHITELIST_CHANNELS:
            return

        content_lower = msg.content.lower()

        if "@everyone" in content_lower or "@here" in content_lower:
            await msg.delete()
            await msg.channel.send(
                f"{msg.author.mention} do not attempt to use @ everyone or @ here.",
                delete_after=5
            )
            await msg.channel.send(
                f"{msg.author.mention} was smited for attempting to use @ everyone or @ here.",
            )
            
        if self.censor_pattern.search(content_lower):
            censored_text = self.censor_message(msg.content)
            files = [await attachment.to_file() for attachment in msg.attachments]
            await msg.channel.send(
                content=f"I've censored {msg.author.mention}'s text: {censored_text}",
                files=files or None,
            )
            await msg.channel.send("Please be mindful of sensitive language usage")
            await msg.delete()

            user_id = msg.author.id
            today = datetime.now(timezone.utc).date()

            if user_id not in self.uncensored_offenses or self.uncensored_offenses[user_id]["date"] != today:
                self.uncensored_offenses[user_id] = {"date": today, "count": 0}

            self.uncensored_offenses[user_id]["count"] += 1
            if self.uncensored_offenses[user_id]["count"] >= 3:
                until = datetime.now(timezone.utc) + timedelta(minutes=1)
                await msg.channel.send(f"{msg.author.mention}, you have used insensitive words 3+ times today.")
                if member:
                    try:
                        await member.timeout(until, reason="Repeated not censoring of words")
                    except discord.Forbidden:
                        pass

        if "kys" in content_lower:
            await msg.delete()
            await msg.channel.send(f"{msg.author.mention} - keep that kind of language to ranked only please")

async def setup(bot):
    await bot.add_cog(_1984(bot))
