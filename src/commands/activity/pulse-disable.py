import discord
from discord import app_commands
from discord.ext import commands

class PulseDisable(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-disable", description="Вимкнути систему Pulse")
    async def pulse_disable(self, interaction: discord.Interaction):
        db = get_database()
        
        # Вимикаємо систему в базі даних
        db.pulse_settings.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {"enabled": False}},
            upsert=True
        )
        
        # Створюємо embed відповідь
        embed = discord.Embed(
            title="⚠️ Систему вимкнено",
            description="Pulse систему було успішно вимкнено",
            color=0xff9900
        )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PulseDisable(bot))