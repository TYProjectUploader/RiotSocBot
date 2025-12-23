# Bot is awaiting riot api approval before fixing other stuff
import os
import discord
import random
import re
import praw
from discord.ext import commands, tasks
from dotenv import load_dotenv
from datetime import datetime, timedelta, timezone

from keep_alive import keep_alive

from bs4 import BeautifulSoup
import urllib3

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")

reddit = praw.Reddit(
    client_id = os.getenv("REDDIT_CLIENT_ID"),
    client_secret= os.getenv("REDDIT_SECRET"),
    user_agent=os.getenv('REDDIT_USER_AGENT')
)

keep_alive()

HTMLPARSER = "html.parser"
RIOT_PATCH_DIVCLASS = "sc-4d29e6fd-0 hzTXxn"
PATCH_ERROR_MSG = "Could not fetch patch notes. Ping @zef to fix"

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.members = True

bot = commands.Bot(command_prefix='>', intents=intents, 
                   help_command=commands.DefaultHelpCommand(no_category="Commands"))

CENSORED_WORDS = {
    "job": r"j\*b",
    "occupation": r"*cc\*p\*t\*\*n",
    "employment": r"\*mpl\*ym\*nt",
    "employed": r"\*mpl\*y\*d",
    "work": r"w\*rk",
    "hire": r"h\*r\*",
    "interview": r"\*nt\*rv\*\*w",
    "intern": r"\*nt\*rn",
    "career": r"c\*r\*\*r",
    "resume": r"r\*s\*m\*",
    "employee": r"\*mpl\*y\*\*",
    "staff": r"st\*ff",
    "wage": r"w\*g\*",
    "salary": r"s\*l\*ry"
}

uncensored_offenses = {} # {user_id: {"date": date, "count": int}}


#startus
@bot.event
async def on_ready():
    print(f"{bot.user.name} is online")
    await bot.change_presence(activity=discord.CustomActivity(name='>help for commands'))

    #loops
    bot.last_posted_lol_patch = None
    bot.last_posted_val_patch = None
    bot.last_posted_tft_patch = None
    check_patch.start()
    daily_meme.start()

# sends DM to member on join
@bot.event
async def on_member_join(member):
    rules_channel = "https://discord.com/channels/312743332579377152/1050317772703416381"
    await member.send(f"Welcome {member.name} to RiotSoc!\n"
                      f"Please read our rules at {rules_channel} to get started\n"
                      "If you need help for anything at all feel free to message an exec or ping a subcom")


def censor_message(content):
    censored = content
    for word, replacement in CENSORED_WORDS.items():
        censored = re.sub(word, replacement, censored, flags=re.IGNORECASE)
    return censored

@bot.event
async def on_raw_message_edit(payload):
    # 'data' contains raw dictionary of the edited message
    data = payload.data
    content = data.get('content', '').lower()
    
    if not content:
        return

    if any(word in content for word in CENSORED_WORDS):
        channel = bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        
        if message.author.bot:
            return

        censored_text = censor_message(message.content)
        await channel.send(f"I've censored {message.author.mention}'s text: {censored_text}")
        await channel.send("Really? You thought that'd work?")
        await channel.send(file=discord.File('neurosig.jpg'))
        
        await message.delete()

@bot.event
async def on_message(msg):
    if msg.author == bot.user:
        return
    
    if msg.mention_everyone:
        await msg.delete()
        await msg.channel.send(
            f"{msg.author.mention} do not use @ everyone or @ here.",
            delete_after=5
        )
        return
    
    if any(word in msg.content.lower() for word in CENSORED_WORDS):
        censored_text = censor_message(msg.content)
        await msg.channel.send(
            f"I've censored {msg.author.mention}'s text: {censored_text}"
        )
        await msg.channel.send(
            "Please be mindful of sensitive language usage"
        )
        await msg.delete()

        user_id = msg.author.id
        today = datetime.now(timezone.utc).date()

        if user_id not in uncensored_offenses or uncensored_offenses[user_id]["date"] != today:
            uncensored_offenses[user_id] = {"date": today, "count": 0}

        uncensored_offenses[user_id]["count"] += 1
        count = uncensored_offenses[user_id]["count"]

        if count >= 3:
            until = datetime.now(timezone.utc) + timedelta(minutes=1)
            await msg.channel.send(
                f"{msg.author.mention}, you have used insensitive words 3+ times today"
                f" I would timeout you if I was able to"
            )
            # Here's where timeout would work if I was properly given perms
            await msg.author.timeout(until, reason="Repeated not censoring of words")

    if "kys" in msg.content.lower():
        await msg.delete()
        await msg.channel.send(f"{msg.author.mention} - keep that kind of language to ranked only please")

    if "clanker" in msg.content.lower():
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


def clean_rank(rank_str):
    """
    Converts "rank tier ??randomno LP" -> "rank tier LP"
    """
    parts = rank_str.split()  # ['Platinum', '4', '4', '0LP']
    if len(parts) == 4:
        return f"{parts[0]} {parts[1]} {parts[3]}"
    elif len(parts) == 3:
        return f"{parts[0]} {parts[2]}"


# ----------------------------
# Rank scraper from opgg
# ----------------------------
def retrieve_rank(server: str, username: str):

    url = f"https://www.op.gg/summoners/{server.lower()}/{username}"
    http = urllib3.PoolManager()
    response = http.request("GET", url, decode_content=True)
    reply = response.data

    soup = BeautifulSoup(reply, HTMLPARSER)

    meta_tag = soup.find("meta", {"property": "og:description"})
    if not meta_tag:
        return None, None

    content = meta_tag.get("content", "")
    # Example content:
    # "DaHoodDuck#Quack / Platinum 4 0LP / 84Win 81Lose Win rate 51% / Brand ..."
    
    parts = [p.strip() for p in content.split("/")]

    rank_info_raw = parts[1] if len(parts) > 1 else "Unknown"

    rank_info = clean_rank(rank_info_raw)

    overall_wr = parts[2] if len(parts) > 2 else "Unknown"

    return rank_info, overall_wr


#rank scraper
@bot.command(name="rank")
async def rank_command(ctx, server: str, *, username: str):
    """
    Gives rank of a summoner >help rank for format
    """

    await ctx.send(f"Fetching rank for **{username}** on **{server.upper()}**...")

    rankinfo, overall_wr = retrieve_rank(server, username.replace("#", "-"))

    if rankinfo is None:
        await ctx.send(f"Could not find rank info for **{username}** on {server.upper()}.\n"
                       f"Either the summoner is unranked, doesn't exist or ping @zef coz bot has issues")
    else:
        parts = overall_wr.split("Win rate")
        games_part = parts[0].strip()       # "104Win 93Lose"
        winrate_part = parts[1].strip()     # "53%"

        winrate_num = int(winrate_part.rstrip("%"))

        emoji = "🥀" if winrate_num < 50 else "🎉"

        embed = discord.Embed(
            title=f"{username} ({server.upper()})",
            description=f"{rankinfo} \n Win rate {winrate_part} {emoji} \n {games_part}",
            color=discord.Color.blue()
        )
        await ctx.send(embed=embed)

@rank_command.error
async def rank_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("❌ Check your formatting!\n"
                       "Usage: `>rank <server> <username#RiotTag>`\n"
                       "Example: `>rank na Faker#NA1`")

@bot.command(name="blame")
async def blame_squid(ctx):
    """
    Blames a random squid
    """
    await ctx.message.delete()
    squids = [467683010213314560, 443721622965452810]
    chosen_id = random.choice(squids)
    user = await bot.fetch_user(chosen_id)
    blame_messages = [
        "is responsible for this chaos!",
        "did it again, blame them!",
        "somehow caused this mess!",
        "is the culprit here!",
        "you know who did it...",
        "ofc this guy would be the one who messed up",
        "totally the mastermind behind this disaster!",
        "should probably be held accountable...",
        "yep, it’s them. no questions.",
        "went above and beyond to make this disaster!",
        "clearly the reason everything is broken!",
        "didn’t even try to hide it this time!",
        "the legend behind today’s catastrophe!",
        "messed up again",
        "definitely the one to blame, as usual!"
    ]

    chosen_message = random.choice(blame_messages)

    await ctx.send(f"{user.mention} {chosen_message}")

@bot.command(name="msgsubcom")
async def msg_subcom(ctx, *, msg):
    """
    Sends a message to be responded to by exec/subcom
    """
    internal_channel = bot.get_channel(1284145136321826817)
    if internal_channel is None:
        ctx.send("Please ping @zef, command has failed")
    else:
        await ctx.send("Your message has been forwarded exec/subcom and you should be responded to soon.")
        await internal_channel.send(f"Message from {ctx.author.mention} in {ctx.channel.mention}: {msg}")

def get_latest_lol_patch():
    http = urllib3.PoolManager()
    url = "https://www.leagueoflegends.com/en-us/news/tags/patch-notes/"
    response = http.request("GET", url, preload_content=True)

    if response.status != 200:
        return None, None

    html = response.data.decode("utf-8")
    soup = BeautifulSoup(html, HTMLPARSER)

    container = soup.find("div", class_=RIOT_PATCH_DIVCLASS)
    if not container:
        return None, None

    a = container.find("a")
    if not a:
        return None, None

    href = a["href"]
    if href.startswith("/"):
        href = "https://www.leagueoflegends.com" + href

    title = a.get("aria-label")
    return title, href

@bot.command(name="lolpatchnotes")
async def lol_patchnotes(ctx):
    """
    Gets latest League of legends patch notes
    """
    title, link = get_latest_lol_patch()
    if not link:
        await ctx.send(PATCH_ERROR_MSG)
    else:
        await ctx.send(f"**{title}**\n{link}")

def get_latest_val_patch():
    http = urllib3.PoolManager()
    url = "https://playvalorant.com/en-us/news/tags/patch-notes/"
    response = http.request("GET", url, preload_content=True)

    if response.status != 200:
        return None, None

    html = response.data.decode("utf-8")
    soup = BeautifulSoup(html, HTMLPARSER)

    container = soup.find("div", class_=RIOT_PATCH_DIVCLASS)
    if not container:
        return None, None

    a = container.find("a")
    if not a:
        return None, None

    href = a["href"]
    if href.startswith("/"):
        href = "https://playvalorant.com" + href

    title = a.get("aria-label")
    return title, href

@bot.command(name="valpatchnotes")
async def val_patchnotes(ctx):
    """
    Gets latest Valorant patch notes
    """
    title, link = get_latest_val_patch()
    if not link:
        await ctx.send(PATCH_ERROR_MSG)
    else:
        await ctx.send(f"**{title}**\n{link}")

def get_latest_tft_patch():
    http = urllib3.PoolManager()
    url = "https://www.leagueoflegends.com/en-au/news/tags/teamfight-tactics-patch-notes/"
    response = http.request("GET", url, preload_content=True)

    if response.status != 200:
        return None, None

    html = response.data.decode("utf-8")
    soup = BeautifulSoup(html, HTMLPARSER)

    container = soup.find("div", class_=RIOT_PATCH_DIVCLASS)
    if not container:
        return None, None

    a = container.find("a")
    if not a:
        return None, None

    href = a["href"]

    title = a.get("aria-label")
    return title, href

@bot.command(name="tftpatchnotes")
async def tft_patchnotes(ctx):
    """
    Gets latest TFT patch notes
    """
    title, link = get_latest_tft_patch()
    if not link:
        await ctx.send(PATCH_ERROR_MSG)
    else:
        await ctx.send(f"**{title}**\n{link}")

# Yes ik its bad code cry about it
@tasks.loop(hours=6)
async def check_patch():
    channel = bot.get_channel(1050307222573428756)
    if channel is None:
        print("❌ Channel not found!")
        return

    title, link = get_latest_lol_patch()

    if title != bot.last_posted_lol_patch:
        await channel.send(f"**LEAGUE OF LEGENDS {title}**\n{link}")
        bot.last_posted_lol_patch = title

    title, link = get_latest_val_patch()

    if title != bot.last_posted_val_patch:
        await channel.send(f"**{title}**\n{link}")
        bot.last_posted_val_patch = title
    
    title, link = get_latest_tft_patch()

    if title != bot.last_posted_tft_patch:
        await channel.send(f"**{title}**\n{link}")
        bot.last_posted_tft_patch = title

def create_meme_embed(submission):
    embed = discord.Embed(
        title="Meme of the day",
        description=submission.title,
        url=f"https://reddit.com{submission.permalink}",
        color=0xFF5700
    )
    
    embed.set_image(url=submission.url)
    
    embed.set_author(
        name="r/leagueofmemes",
        icon_url="https://www.redditstatic.com/desktop2x/img/favicon/apple-icon-57x57.png",
        url="https://reddit.com/r/leagueofmemes"
    )
    author = submission.author.name if submission.author else "[deleted]"
    embed.set_footer(text=f"👤 u/{author}")
    return embed


@tasks.loop(hours=24)
async def daily_meme():
    meme_channel = bot.get_channel(1050306304083775558)
    if meme_channel is None:
        print("❌ Channel not found!")
        return
    submission = next(reddit.subreddit('leagueofmemes').top(time_filter='day', limit=1))

    if submission and submission.url:
        embed = create_meme_embed(submission)
        await meme_channel.send(embed=embed)
    else:
        await meme_channel.send("ping @zef somethings gone wrong")

@bot.command()
@commands.has_role("Subcommittee")
async def secretcmd(ctx):
    await ctx.send("You have access, this does nothing xd")

@secretcmd.error 
async def secrectcmd_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You don't have perms to do that")

bot.run(TOKEN)
