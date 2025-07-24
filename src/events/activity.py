import discord
from discord.ext import commands, tasks
from datetime import datetime
import json
import os

DATA_FILE = '../xp_data.json'
LEVEL_UP_CHANNEL_NAME = "bots"

def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def ensure_user(data, guild_id, user_id):
    if str(guild_id) not in data:
        data[str(guild_id)] = {}
    if str(user_id) not in data[str(guild_id)]:
        data[str(guild_id)][str(user_id)] = {
            "xp": 0,
            "level": 1,
            "messages": 0,
            "voice_minutes": 0,
            "reactions": 0,
            "history": {}
        }
    user_data = data[str(guild_id)][str(user_id)]
    if "history" not in user_data:
        user_data["history"] = {}
    return user_data

def get_level_xp(level):
    return 5 * (level ** 2) + 50 * level + 100

async def level_up_check(message, user_data):
    needed_xp = get_level_xp(user_data["level"])
    if user_data["xp"] >= needed_xp:
        user_data["xp"] -= needed_xp
        user_data["level"] += 1

        channel = discord.utils.get(message.guild.text_channels, name=LEVEL_UP_CHANNEL_NAME)
        if channel:
            await channel.send(f"{message.author.mention} підвищив рівень до {user_data['level']}!")

class ActivityEvents(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.update_voice_time.start()

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
        data = load_data()
        user_data = ensure_user(data, message.guild.id, message.author.id)

        user_data["xp"] += 10
        user_data["messages"] += 1

        today = datetime.now().strftime("%Y-%m-%d")
        user_data["history"][today] = user_data["history"].get(today, 0) + 10

        await level_up_check(message, user_data)
        save_data(data)

    @commands.Cog.listener()
    async def on_reaction_add(self, reaction, user):
        if user.bot:
            return
        data = load_data()
        user_data = ensure_user(data, reaction.message.guild.id, user.id)

        user_data["xp"] += 2
        user_data["reactions"] += 1

        today = datetime.now().strftime("%Y-%m-%d")
        user_data["history"][today] = user_data["history"].get(today, 0) + 2

        save_data(data)

    @tasks.loop(minutes=1)
    async def update_voice_time(self):
        for guild in self.bot.guilds:
            for vc in guild.voice_channels:
                for member in vc.members:
                    if not member.bot:
                        data = load_data()
                        user_data = ensure_user(data, guild.id, member.id)

                        user_data["xp"] += 5
                        user_data["voice_minutes"] += 1

                        today = datetime.now().strftime("%Y-%m-%d")
                        user_data["history"][today] = user_data["history"].get(today, 0) + 5

                        save_data(data)

async def setup(bot):
    await bot.add_cog(ActivityEvents(bot))