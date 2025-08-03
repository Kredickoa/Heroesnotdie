import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database

db = get_database()

class LevelPingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="levelping", description="Увімкнути/вимкнути пінги при підвищенні рівня")
    async def levelping(self, interaction: discord.Interaction):
        user_id = interaction.user.id

        user_data = await db.users.find_one({"user_id": user_id, "guild_id": interaction.guild.id})
        current_state = True  # за замовчуванням пінги увімкнені
        if user_data and "allow_level_ping" in user_data:
            current_state = user_data["allow_level_ping"]

        new_state = not current_state

        await db.users.update_one(
            {"user_id": user_id, "guild_id": interaction.guild.id},
            {"$set": {"allow_level_ping": new_state}},
            upsert=True
        )

        if new_state:
            msg = "🔔 Пінги при левелапі **увімкнено**."
        else:
            msg = "🔕 Пінги при левелапі **вимкнено**."

        await interaction.response.send_message(msg, ephemeral=True)
async def setup(bot):
    await bot.add_cog(LevelPingCommand(bot))
