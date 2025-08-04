import discord
from discord import app_commands
from discord.ext import commands
from database import get_database
from datetime import datetime, timedelta

class PulseCheck(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pulse-check", description="Виконати ручну перевірку активності")
    async def pulse_check(self, interaction: discord.Interaction):
        db = get_database()
        
        # Отримуємо налаштування з бази даних
        settings = db.pulse_settings.find_one({"guild_id": interaction.guild.id})
        
        if not settings or not settings.get("enabled", False):
            embed = discord.Embed(
                title="❌ Помилка",
                description="Система не налаштована",
                color=0xff0000
            )
            await interaction.response.send_message(embed=embed)
            return
        
        # Відкладена відповідь бо перевірка може тривати довго
        await interaction.response.defer()
        
        # Отримуємо роль
        role = interaction.guild.get_role(settings["role_id"])
        if not role:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Роль не знайдена",
                color=0xff0000
            )
            await interaction.followup.send(embed=embed)
            return
        
        added_roles = 0
        removed_roles = 0
        
        # Дата 5 днів тому
        five_days_ago = datetime.now() - timedelta(days=5)
        
        # Перевіряємо всіх користувачів сервера
        for member in interaction.guild.members:
            if member.bot:
                continue
            
            # Отримуємо дані користувача з бази даних
            user_data = db.users.find_one({"user_id": member.id, "guild_id": interaction.guild.id})
            
            if not user_data:
                continue
            
            # Рахуємо XP за останні 5 днів
            xp_last_5_days = 0
            if "xp_history" in user_data:
                for record in user_data["xp_history"]:
                    if datetime.fromisoformat(record["date"]) >= five_days_ago:
                        xp_last_5_days += record["xp"]
            
            current_level = user_data.get("level", 0)
            has_role = role in member.roles
            
            # Перевіряємо чи відповідає умовам
            meets_requirements = (current_level >= settings["min_level"] and 
                                xp_last_5_days >= settings["min_xp"])
            
            # Додаємо або забираємо роль
            if meets_requirements and not has_role:
                await member.add_roles(role)
                added_roles += 1
            elif not meets_requirements and has_role:
                await member.remove_roles(role)
                removed_roles += 1
        
        # Створюємо embed відповідь
        embed = discord.Embed(
            title="✅ Перевірку завершено",
            description="Результати ручної перевірки активності:",
            color=0x00ff00
        )
        
        embed.add_field(name="Додано ролей:", value=str(added_roles), inline=True)
        embed.add_field(name="Знято ролей:", value=str(removed_roles), inline=True)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PulseCheck(bot))