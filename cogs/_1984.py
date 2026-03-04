import discord
import re
import os
import random
from discord.ext import commands
from datetime import datetime, timedelta, timezone

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
                os.getenv("DIRECTOR_ROLE_ID")
            )
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

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        if payload.channel_id in self.WHITE_LIST_CHANNELS:
            return
        if any(role.id in self.WHITELIST_ROLES for role in msg.author.roles):
            return

        if payload.channel_id in self.WHITELIST_CHANNELS:
            return
        
        if payload.guild_id in self.WHITELIST_GUILDS:
            return

        # 'data' contains raw dictionary of the edited message
        data = payload.data
        content = data.get('content', '').lower()
        
        if not content: return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        if any(role.id in self.WHITELIST_ROLES for role in message.author.roles):
            return

        if self.censor_pattern.search(content):
            if message.author.bot: return

            censored_text = self.censor_message(message.content)
            files = [await attachment.to_file() for attachment in msg.attachments]
            await channel.send(content=f"I've censored {message.author.mention}'s text: {censored_text}", files=files)
            await channel.send("Really? You thought editing your message would let you bypass me?")
            await channel.send(file=discord.File('neurosig.jpg'), delete_after=5)
            await message.delete()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.channel.id in self.WHITE_LIST_CHANNELS:
            return
        if msg.author.bot: return
        
        if any(role.id in self.WHITELIST_ROLES for role in msg.author.roles):
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
            
        if self.censor_pattern.search(content_lower):
            censored_text = self.censor_message(msg.content)
            files = [await attachment.to_file() for attachment in msg.attachments]
            await msg.channel.send(content=f"I've censored {msg.author.mention}'s text: {censored_text}", files=files)
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
                try:
                    await msg.author.timeout(until, reason="Repeated not censoring of words")
                except discord.Forbidden:
                    pass

        if "kys" in content_lower:
            await msg.delete()
            await msg.channel.send(f"{msg.author.mention} - keep that kind of language to ranked only please")

async def setup(bot):
    await bot.add_cog(_1984(bot))