import discord
from discord import app_commands
from discord.ext import commands

class PulseStatus(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-status", description="Показати статус системи Pulse")
    async def pulse_status(self, interaction: discord.Interaction):
        db = get_database()
        
        # Отримуємо налаштування з бази даних
        settings = db.pulse_settings.find_one({"guild_id": interaction.guild.id})
        
        if not settings or not settings.get("enabled", False):
            embed = discord.Embed(
                title="❌ Система вимкнена",
                description="Pulse система не налаштована",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Отримуємо роль та кількість учасників з нею
        role = interaction.guild.get_role(settings["role_id"])
        members_with_role = len(role.members) if role else 0
        
        # Створюємо embed відповідь
        embed = discord.Embed(
            title="📊 Статус Pulse",
            description="Поточні налаштування системи:",
            color=0x0099ff
        )
        
        embed.add_field(name="Роль:", value=f"@{settings['role_name']}", inline=False)
        embed.add_field(name="Мін. рівень:", value=str(settings["min_level"]), inline=True)
        embed.add_field(name="Мін. XP за 5 днів:", value=str(settings["min_xp"]), inline=True)
        embed.add_field(name="Учасників з роллю:", value=str(members_with_role), inline=True)
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PulseStatus(bot))