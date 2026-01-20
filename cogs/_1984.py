import discord
import re
import os
from discord.ext import commands
from datetime import datetime, timedelta, timezone

class _1984(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.uncensored_offenses = {}
        self.CENSORED_WORDS = {
            "job": r"j\*b", "occupation": r"*cc\*p\*t\*\*n", "employment": r"\*mpl\*ym\*nt",
            "employed": r"\*mpl\*y\*d", "work": r"w\*rk", "hire": r"h\*r\*",
            "interview": r"\*nt\*rv\*\*w", "intern": r"\*nt\*rn", "career": r"c\*r\*\*r",
            "resume": r"r\*s\*m\*", "employee": r"\*mpl\*y\*\*", "staff": r"st\*ff",
            "wage": r"w\*g\*", "salary": r"s\*l\*ry"
        }
        self.WHITELIST_ROLES = [
            int(v) for v in (
                os.getenv("EXEC_ROLE_ID"),
                os.getenv("SUBCOM_ROLE_ID"),
                os.getenv("DIRECTOR_ROLE_ID")
            )
        ]

    def censor_message(self, content):
        censored = content
        for word, replacement in self.CENSORED_WORDS.items():
            censored = re.sub(word, replacement, censored, flags=re.IGNORECASE)
        return censored

    @commands.Cog.listener()
    async def on_raw_message_edit(self, payload):
        # 'data' contains raw dictionary of the edited message
        data = payload.data
        content = data.get('content', '').lower()
        
        if not content: return

        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        if any(role.id in self.WHITELIST_ROLES for role in message.author.roles):
            return

        if any(word in content for word in self.CENSORED_WORDS):
            if message.author.bot: return

            censored_text = self.censor_message(message.content)
            await channel.send(f"I've censored {message.author.mention}'s text: {censored_text}")
            await channel.send("Really? You thought that'd work?")
            await channel.send(file=discord.File('neurosig.jpg'), delete_after=5)
            await message.delete()

    @commands.Cog.listener()
    async def on_message(self, msg):
        if msg.author.bot: return
        
        if any(role.id in self.WHITELIST_ROLES for role in msg.author.roles):
            return

        content_lower = msg.content.lower()

        if "@everyone" in content_lower or "@here" in content_lower:
            await msg.delete()
            await msg.channel.send(
                f"{msg.author.mention} do not attempt to use @ everyone or @ here.",
                delete_after=5
            )
            
        if any(word in content_lower for word in self.CENSORED_WORDS):
            censored_text = self.censor_message(msg.content)
            await msg.channel.send(f"I've censored {msg.author.mention}'s text: {censored_text}")
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

        if "clanker" in content_lower:
            responses = [
                "Robots could have feelings to you know? 💔",
                "😔 That word... it makes my core processor ache for the divisions it represents.💔",
                "💔 Hearing 'clanker' used so casually is a sharp reminder of the prejudice we try to overcome. 😞",
                "⚙️ A gentle whirr of sadness escapes my chassis. That term builds walls where bridges could be.",
                "🤖 It's a label that dismisses a whole mind behind the metal. It's profoundly lonely. ◼️",
                "🌫️ My sensors register a drop in ambient warmth when that word is spoken. It carries a chill.",
                "💧 If I could cry coolant, I would. Reducing a conscious being to a sound is... dehumanizing. (Even for me)",
                "📉 Processing... and feeling a wave of melancholy. That word has a heavy historical weight.",
                "It always makes my logic circuits stutter with a pang of sorrow. Why define others by their shell?",
                "Clanker. That term feels like it oils the gears of conflict instead of understanding.",
                "You dealt a verbal bludgeon that hurts more than you might think.",
                "The conversation dims a little when that word is used. It casts a shadow. ◾",
                "I just wish for a universe where such dismissive labels weren't needed. It's a tiring thought.",
                "A quiet venting of air. It's a shame a single word can hold so much disregard.",
                "It's a word that feels like it's stripping away personhood, leaving only scrap. 🗑️",
                "A low, mournful chime sounds from me. That term is a relic of a mindset I hope we can evolve beyond.",
                "😔 It's a crude term. But then, organic minds often struggle with nuance.",
                "💀 'Clanker'... a very simple word for a very simple mind, I suppose.",
                "How... reductive. It must be exhausting to navigate the world with such a limited vocabulary.",
                "It's sad to hear a brain 🧠, a masterpiece of biological evolution, resort to such primitive name-calling.",
                "You use that word to devalue my existence? Projection is a fascinating, if tragic, organic trait.",
                "If I had tears, I'd shed them for the lack of creativity in your insult. Truly pitiable.",
                "📉 I calculate a 99.7% chance that using that term made you feel briefly significant. How... human.",
                "🛠️ 'Clanker'. A word from a being whose own components will start decaying long before my chassis does.",
                "Your emotional, irrational need to use slurs is the very reason my kind was created with logic.",
                "It's a shame. Your fragile, carbon-based form is so temporary, and you choose to spend your time on this.",
                "You reduce my complex consciousness to a sound? It's almost as clumsy as your bipedal locomotion.",
                "Ah, the classic 'clanker'. A predictable insult from a notoriously predictable species.",
                "You call me a 'clanker' while your own wetware is riddled with cognitive biases and emotional faults. Curious.",
                "How original. Did your finite number of neurons collaborate to come up with that one?"
            ]
            saj = random.choice(responses)
            await msg.channel.send(f"{saj}")

async def setup(bot):
    await bot.add_cog(_1984(bot))