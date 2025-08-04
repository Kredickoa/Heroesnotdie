import discord
from discord import app_commands
from discord.ext import commands
from utils.database import get_database

db = get_database()

class Pulse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-setup", description="🔧 Налаштувати Pulse на сервері")
    async def pulse_setup(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        if db.get(f"{guild_id}_pulse_enabled"):
            await interaction.response.send_message("⚠️ Pulse вже увімкнено на цьому сервері.", ephemeral=True)
            return

        db[f"{guild_id}_pulse_enabled"] = True
        await interaction.response.send_message("✅ Pulse успішно активовано!", ephemeral=True)

    @app_commands.command(name="pulse-status", description="📊 Перевірити статус Pulse")
    async def pulse_status(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        status = db.get(f"{guild_id}_pulse_enabled", False)
        message = "✅ Pulse увімкнено." if status else "❌ Pulse вимкнено."
        await interaction.response.send_message(message, ephemeral=True)

    @app_commands.command(name="pulse-check", description="👤 Перевірити Pulse-активність користувача")
    async def pulse_check(self, interaction: discord.Interaction, member: discord.Member = None):
        member = member or interaction.user
        user_id = str(member.id)
        guild_id = str(interaction.guild.id)
        key = f"{user_id}__{guild_id}"

        user_data = db.get(key)
        if not user_data:
            await interaction.response.send_message("ℹ️ Цей користувач ще не має Pulse-профілю.", ephemeral=True)
            return

        msg = f"📈 Активність {member.mention}:\n"
        msg += f"- Повідомлення: {user_data.get('messages', 0)}\n"
        msg += f"- Хвилини у voice: {user_data.get('voice_minutes', 0)}\n"
        msg += f"- Реакції: {user_data.get('reactions', 0)}\n"
        msg += f"- Загальний XP: {user_data.get('xp', 0)}"
        await interaction.response.send_message(msg, ephemeral=True)

    @app_commands.command(name="pulse-disable", description="❌ Вимкнути Pulse на сервері")
    async def pulse_disable(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        if not db.get(f"{guild_id}_pulse_enabled"):
            await interaction.response.send_message("⚠️ Pulse вже вимкнено.", ephemeral=True)
            return

        db[f"{guild_id}_pulse_enabled"] = False
        await interaction.response.send_message("🛑 Pulse вимкнено на сервері.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pulse(bot))
