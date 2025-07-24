import discord
from discord import app_commands
from discord.ext import commands
import json
import os

DATA_FILE = '../xp_data.json'

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
    return data[str(guild_id)][str(user_id)]

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addxp", description="Додати XP")
    @app_commands.describe(user="Кому додати", amount="Скільки XP")
    async def add_xp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        data = load_data()
        user_data = ensure_user(data, interaction.guild.id, user.id)
        user_data["xp"] += amount
        save_data(data)
        await interaction.response.send_message(f"✅ {amount} XP додано {user.mention}.", ephemeral=True)

    @app_commands.command(name="removexp", description="Забрати XP")
    @app_commands.describe(user="У кого забрати", amount="Скільки XP")
    async def remove_xp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        data = load_data()
        user_data = ensure_user(data, interaction.guild.id, user.id)
        user_data["xp"] = max(user_data["xp"] - amount, 0)
        save_data(data)
        await interaction.response.send_message(f"🗑️ {amount} XP забрано у {user.mention}.", ephemeral=True)

    @app_commands.command(name="setlevel", description="Задати рівень")
    @app_commands.describe(user="Кому", level="Новий рівень")
    async def set_level(self, interaction: discord.Interaction, user: discord.Member, level: int):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        data = load_data()
        user_data = ensure_user(data, interaction.guild.id, user.id)
        user_data["level"] = level
        save_data(data)
        await interaction.response.send_message(f"🔧 Рівень {user.mention} встановлено на {level}.", ephemeral=True)

    @app_commands.command(name="resetxp", description="Скинути XP")
    @app_commands.describe(user="Кому")
    async def reset_xp(self, interaction: discord.Interaction, user: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        data = load_data()
        user_data = ensure_user(data, interaction.guild.id, user.id)
        user_data["xp"] = 0
        save_data(data)
        await interaction.response.send_message(f"🔄 XP {user.mention} скинуто до 0.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))