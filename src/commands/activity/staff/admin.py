import discord
from discord import app_commands
from discord.ext import commands
import json
from modules.db import get_database

db = get_database()

def is_admin_or_dev(user_id):
    try:
        with open("../config.json", "r", encoding="utf-8") as f:
            config = json.load(f)
        return user_id in config.get("dev", [])
    except:
        return False

def check_permissions(interaction):
    return interaction.user.guild_permissions.administrator or is_admin_or_dev(interaction.user.id)

async def get_user_data(guild_id, user_id):
    user = await db.users.find_one({"guild_id": guild_id, "user_id": user_id})
    if not user:
        user = {
            "guild_id": guild_id,
            "user_id": user_id,
            "xp": 0,
            "level": 1,
            "messages": 0,
            "voice_minutes": 0,
            "reactions": 0,
            "history": {}
        }
        await db.users.insert_one(user)
    return user

async def update_user_data(guild_id, user_id, update_data):
    await db.users.update_one(
        {"guild_id": guild_id, "user_id": user_id},
        {"$set": update_data}
    )

class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="addxp", description="Додати XP")
    @app_commands.describe(user="Кому додати", amount="Скільки XP")
    async def add_xp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if not check_permissions(interaction):
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        user_data = await get_user_data(interaction.guild.id, user.id)
        await update_user_data(interaction.guild.id, user.id, {"xp": user_data["xp"] + amount})
        await interaction.response.send_message(f"✅ {amount} XP додано {user.mention}.", ephemeral=True)

    @app_commands.command(name="removexp", description="Забрати XP")
    @app_commands.describe(user="У кого забрати", amount="Скільки XP")
    async def remove_xp(self, interaction: discord.Interaction, user: discord.Member, amount: int):
        if not check_permissions(interaction):
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        user_data = await get_user_data(interaction.guild.id, user.id)
        await update_user_data(interaction.guild.id, user.id, {"xp": max(user_data["xp"] - amount, 0)})
        await interaction.response.send_message(f"🗑️ {amount} XP забрано у {user.mention}.", ephemeral=True)

    @app_commands.command(name="setlevel", description="Задати рівень")
    @app_commands.describe(user="Кому", level="Новий рівень")
    async def set_level(self, interaction: discord.Interaction, user: discord.Member, level: int):
        if not check_permissions(interaction):
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        user_data = await get_user_data(interaction.guild.id, user.id)
        await update_user_data(interaction.guild.id, user.id, {"level": level})
        await interaction.response.send_message(f"🔧 Рівень {user.mention} встановлено на {level}.", ephemeral=True)

    @app_commands.command(name="resetxp", description="Скинути XP")
    @app_commands.describe(user="Кому")
    async def reset_xp(self, interaction: discord.Interaction, user: discord.Member):
        if not check_permissions(interaction):
            await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
            return
        user_data = await get_user_data(interaction.guild.id, user.id)
        await update_user_data(interaction.guild.id, user.id, {"xp": 0})
        await interaction.response.send_message(f"🔄 XP {user.mention} скинуто до 0.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCommands(bot))