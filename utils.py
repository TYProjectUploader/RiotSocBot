import json
import os

import discord

DATA_FILE = "data.json"

def get_persist():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return {}

def update_persist(key, value):
    data = get_persist()
    data[key] = value
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)

async def get_text_channel(bot: discord.Client, channel_id: int):
    channel = bot.get_channel(channel_id)
    if channel is None:
        try:
            channel = await bot.fetch_channel(channel_id)
        except discord.HTTPException:
            return None
    return channel if isinstance(channel, discord.abc.Messageable) else None
