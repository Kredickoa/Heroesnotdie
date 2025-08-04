import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database

db = get_database()

class Pulse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-setup", description="Налаштувати Pulse систему на сервері")
    async def pulse_setup(self, interaction: discord.Interaction, role: discord.Role, hp_threshold: int):
        guild_id = str(interaction.guild.id)
        collection = db["pulse_settings"]

        existing = await collection.find_one({"_id": guild_id})
        if existing:
            await interaction.response.send_message("⚠️ Pulse вже активовано на цьому сервері.", ephemeral=True)
            return

        await collection.insert_one({
            "_id": guild_id,
            "enabled": True,
            "role_id": role.id,
            "hp_threshold": hp_threshold
        })
        await interaction.response.send_message(f"✅ Pulse система активована! Роль {role.name} буде видаватися за {hp_threshold} хп за 7 днів.", ephemeral=True)

        # Перевірка та видача ролі одразу після налаштування
        member = interaction.user
        level = 5  # Припустимо, що рівень береться з іншої системи (замінити на реальну логіку)
        if level >= 5:  # Перевірка, чи користувач на 5-му рівні або вище
            await member.add_roles(role)
            await interaction.followup.send(f"✅ Роль {role.name} видана вам, оскільки ваш рівень ({level}) відповідає умовам!", ephemeral=True)

    @app_commands.command(name="pulse-status", description="Перевірити статус Pulse системи")
    async def pulse_status(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        collection = db["pulse_settings"]
        data = await collection.find_one({"_id": guild_id})

        if data and data.get("enabled"):
            role = interaction.guild.get_role(data["role_id"])
            await interaction.response.send_message(f"✅ Pulse система увімкнена. Роль: {role.name}, ХП за 7 днів: {data['hp_threshold']}.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Pulse система вимкнена.", ephemeral=True)

    @app_commands.command(name="pulse-disable", description="Вимкнути Pulse систему на сервері")
    async def pulse_disable(self, interaction: discord.Interaction):
        guild_id = str(interaction.guild.id)
        collection = db["pulse_settings"]

        existing = await collection.find_one({"_id": guild_id})
        if existing:
            await collection.delete_one({"_id": guild_id})
            await interaction.response.send_message("❌ Pulse система вимкнена та дані видалені.", ephemeral=True)
        else:
            await interaction.response.send_message("⚠️ Pulse система вже вимкнена.", ephemeral=True)

    @app_commands.command(name="pulse-check", description="Ручна перевірка активності")
    async def pulse_check(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔄 Ручна перевірка активності запущена.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Pulse(bot))