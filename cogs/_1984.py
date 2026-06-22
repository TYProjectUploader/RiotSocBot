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

_URL_PATTERN = re.compile(r'https?://\S+')

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
                ## os.getenv("EXEC_ROLE_ID"),
                ## os.getenv("DIRECTOR_ROLE_ID"),
                os.getenv("RIOT_ROLE_ID"),
            ) if v
        ]
        self.WHITELIST_GUILDS = {1464920295881314304}

        self.WHITE_LIST_CHANNELS = [
            312748799799984130,
            123456789012345678,
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

    def _neutralise_mass_pings(self, text: str) -> str:
        """Break @everyone/@here so Discord cannot mass-ping from bot messages."""
        def break_ping(match: re.Match[str]) -> str:
            return "@" + "\u200b" + match.group()[1:]

        text = re.sub(r"@everyone", break_ping, text, flags=re.IGNORECASE)
        return re.sub(r"@here", break_ping, text, flags=re.IGNORECASE)

    ## make sure even if it slips through it can't metnion
    def _mass_ping_allowed_mentions(self, author: discord.abc.User) -> discord.AllowedMentions:
        return discord.AllowedMentions(everyone=False, roles=False, users=[author])

    async def _send_mass_ping_reply(self, channel: discord.abc.Messageable, author: discord.abc.User, body: str):
        mention = author.mention
        safe_body = self._neutralise_mass_pings(body)
        max_body = max(0, 2000 - len(mention) - 2)
        await channel.send(
            f"{mention} Don't even try to use @ everyone or @ here in your message, it's not allowed.\n{safe_body[:max_body]}",
            files=[discord.File('lulu_squash.jpg')],
            allowed_mentions=self._mass_ping_allowed_mentions(author),
        )

    async def _send_as_author(
        self,
        channel: discord.TextChannel,
        author: discord.abc.User,
        content: str,
        message: discord.Message | None = None,
    ) -> bool:
        files = []
        if message:
            files = [await attachment.to_file() for attachment in message.attachments]
        file_kwargs = {"files": files} if files else {}

        try:
            webhook = await channel.create_webhook(name="RiotSocBot")
            try:
                await webhook.send(
                    content[:2000],
                    username=author.display_name,
                    avatar_url=author.display_avatar.url,
                    **file_kwargs,
                )
            finally:
                await webhook.delete()
            return True
        except discord.Forbidden:
            await channel.send(f"{author.mention} {content[:2000]}", **file_kwargs)
            return True
        except discord.HTTPException:
            logger.exception("webhook send as author failed for user %s", author.id)
            return False

    async def _replace_with_censored(self, channel: discord.TextChannel, message: discord.Message) -> bool:
        censored_text = self.censor_message(message.content)
        if not await self._send_as_author(channel, message.author, censored_text, message):
            return False
        await message.delete()
        return True

    def _owoify_segment(self, text: str) -> str:
        if not text:
            return text
        leading_match = re.match(r'^\s+', text)
        leading = leading_match.group(0) if leading_match else ''
        trailing_match = re.search(r'\s+$', text)
        trailing = trailing_match.group(0) if trailing_match else ''
        middle = text[len(leading):len(text) - len(trailing) if trailing else len(text)]
        return leading + (owoify(middle, Owoness.Owo) if middle else '') + trailing

    def _is_user_content_edit(self, payload: discord.RawMessageUpdateEvent, content: str) -> bool:
        data = payload.data or {}
        # Discord sends MESSAGE_UPDATE when embeds/previews attach, without edited_timestamp.
        if 'edited_timestamp' not in data:
            return False
        cached = payload.cached_message
        if cached is not None and cached.content == content:
            return False
        return True

    def _owoify_preserving_urls(self, content: str) -> str:
        parts: list[str] = []
        urls: list[str] = []
        last_end = 0
        for match in _URL_PATTERN.finditer(content):
            parts.append(content[last_end:match.start()])
            urls.append(match.group(0))
            last_end = match.end()
        parts.append(content[last_end:])

        result: list[str] = []
        for i, part in enumerate(parts):
            result.append(self._owoify_segment(part))
            if i < len(urls):
                result.append(urls[i])
        return ''.join(result)

    async def _owoify_edit_prank(self, channel: discord.TextChannel, message: discord.Message, content: str):
        if message.author.bot or random.randint(1, 7) != 1:
            return

        owoified = self._owoify_preserving_urls(content)
        if await self._send_as_author(channel, message.author, owoified, message):
            await message.delete()

    # responsds to a mass ping
    async def _respond_to_mass_ping(self, channel: discord.abc.Messageable, author: discord.abc.User, content: str):
        ping_type = "@everyone" if "@everyone" in content.lower() else "@here"
        fallback_body = (
            f"Blocked a {ping_type} ping. "
            "Treat unexpected mass pings as suspicious—do not click links or share credentials."
        )

        random_stuff = self.bot.get_cog("RandomStuff")
        if not random_stuff:
            await self._send_mass_ping_reply(channel, author, fallback_body)
            return

        prompt = (
            f"{author.display_name} tried to mass-ping a discord server ({ping_type}) with this message:\n"
            f"---\n{content}\n---\n"
            "Say that their message was blocked because it was a mass ping."
            "If it resembles a scam (phishing, fake Nitro, crypto/airdrop, free macbook/camera/ps5/etc, impersonation, urgency + suspicious links), "
            "warn the server not to click links or trust the user who posted it"
            "Never write @everyone or @here in your reply."
        )

        try:
            async with channel.typing():
                response = await random_stuff.mistral_client.chat.complete_async(
                    model=random_stuff.model_id,
                    messages=[
                        {"role": "system", "content": random_stuff.system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.7,
                )
            text = (response.choices[0].message.content or "").strip()
            await self._send_mass_ping_reply(channel, author, text or fallback_body)
        except Exception:
            logger.exception("mass ping Mistral response failed")
            await self._send_mass_ping_reply(channel, author, fallback_body)

    async def _censor_violation(self, channel: discord.TextChannel, message: discord.Message, followup: str):
        if not await self._replace_with_censored(channel, message):
            return
        await channel.send(followup)
        await channel.send(files=[discord.File('neurosig.jpg')], delete_after=5)

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload: discord.RawMessageUpdateEvent):
        if payload.channel_id in self.WHITE_LIST_CHANNELS:
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
        if not self._is_user_content_edit(payload, content):
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

        if msg.channel.id in self.WHITE_LIST_CHANNELS:
            return

        content_lower = msg.content.lower()

        if "@everyone" in content_lower or "@here" in content_lower:
            original_content = msg.content
            await msg.delete()
            await self._respond_to_mass_ping(msg.channel, msg.author, original_content)
            return

        if self.censor_pattern.search(content_lower):
            if isinstance(msg.channel, discord.TextChannel):
                await self._replace_with_censored(msg.channel, msg)
            await msg.channel.send("Please be mindful of sensitive language usage")

            user_id = msg.author.id
            today = datetime.now(timezone.utc).date()

            if user_id not in self.uncensored_offenses or self.uncensored_offenses[user_id]["date"] != today:
                self.uncensored_offenses[user_id] = {"date": today, "count": 0}

            self.uncensored_offenses[user_id]["count"] += 1
            if self.uncensored_offenses[user_id]["count"] >= 3:
                until = datetime.now(timezone.utc) + timedelta(minutes=1)
                await msg.channel.send(f"{msg.author.mention}, you have used insensitive words 3+ times today. Reflect on your actions.")
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
