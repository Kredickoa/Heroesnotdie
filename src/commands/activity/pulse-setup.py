import discord
from discord import app_commands
from discord.ext import commands
from database import get_database

class PulseSetup(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-setup", description="Налаштувати систему Active Ping")
    @app_commands.describe(
        role="Роль для активних гравців",
        min_level="Мінімальний рівень (за замовчуванням: 5)",
        min_xp="Мінімальний XP за 5 днів (за замовчуванням: 300)"
    )
    async def pulse_setup(
        self, 
        interaction: discord.Interaction, 
        role: discord.Role,
        min_level: int = 5,
        min_xp: int = 300
    ):
        db = get_database()
        
        # Зберігаємо налаштування в базу даних
        db.pulse_settings.update_one(
            {"guild_id": interaction.guild.id},
            {
                "$set": {
                    "guild_id": interaction.guild.id,
                    "enabled": True,
                    "role_id": role.id,
                    "role_name": role.name,
                    "min_level": min_level,
                    "min_xp": min_xp
                }
            },
            upsert=True
        )
        
        # Створюємо embed відповідь
        embed = discord.Embed(
            title="✅ Pulse налаштовано!",
            description="Система активних ролей успішно налаштована",
            color=0x00ff00
        )
        
        embed.add_field(name="Роль:", value=f"@{role.name}", inline=False)
        embed.add_field(name="Мін. рівень:", value=str(min_level), inline=True)
        embed.add_field(name="Мін. XP за 5 днів:", value=str(min_xp), inline=True)
        embed.set_footer(text="ℹ️ Інформація:\nПеревірка активності відбувається автоматично кожні 24 години.")
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PulseSetup(bot))