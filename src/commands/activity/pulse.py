import discord
from discord import app_commands
from discord.ext import commands
from models.db import get_database  # Імпорт за твоєю структурою

db = get_database()

class Pulse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-setup", description="Налаштувати Pulse систему на сервері")
    async def pulse_setup(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        collection = db["pulse_settings"]

        if collection.find_one({"_id": guild_id}):
            await interaction.response.send_message("⚠️ Pulse вже активовано на цьому сервері.", ephemeral=True)
            return

        collection.insert_one({"_id": guild_id, "enabled": True})
        await interaction.response.send_message("✅ Pulse система активована!", ephemeral=True)

    @app_commands.command(name="pulse-status", description="Перевірити статус Pulse системи")
    async def pulse_status(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        collection = db["pulse_settings"]
        data = collection.find_one({"_id": guild_id})

        if data and data.get("enabled"):
            await interaction.response.send_message("✅ Pulse система увімкнена.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Pulse система вимкнена.", ephemeral=True)

    @app_commands.command(name="pulse-disable", description="Вимкнути Pulse систему на сервері")
    async def pulse_disable(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        collection = db["pulse_settings"]

        if collection.find_one({"_id": guild_id}):
            collection.delete_one({"_id": guild_id})
            await interaction.response.send_message("❌ Pulse система вимкнена та дані видалені.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Pulse система вже вимкнена.", ephemeral=True)

    @app_commands.command(name="pulse-check", description="Ручна перевірка активності")
    async def pulse_check(self, interaction: discord.Interaction):
        # TODO: Додати логіку перевірки активності
        await interaction.response.send_message("🔄 Ручна перевірка активності запущена.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pulse(bot))
