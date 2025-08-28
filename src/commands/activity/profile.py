import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import uuid
import os
from modules.db import get_database

db = get_database()

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

def get_level_xp(level):
    return 5 * (level ** 2) + 50 * level + 100

class ProfileCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="profile", description="Показує профіль користувача")
    @app_commands.describe(user="Користувач (за замовчуванням - ти)")
    async def profile(self, interaction: discord.Interaction, user: discord.Member = None):
        await interaction.response.defer(ephemeral=False)

        try:
            target_user = user or interaction.user
            user_data = await get_user_data(interaction.guild.id, target_user.id)

            current_level = user_data.get("level", 0)
            xp = user_data.get("xp", 0)
            xp_needed = get_level_xp(current_level)
            xp_percent = round((xp / xp_needed) * 100) if xp_needed else 0
            
            # Конвертуємо хвилини в години
            voice_minutes = user_data.get("voice_minutes", 0)
            voice_hours = round(voice_minutes / 60, 1)
            
            roles = [
                role.name for role in sorted(target_user.roles, key=lambda r: r.position, reverse=True)
                if role.name != "@everyone"
            ][:3]
            roles_display = ", ".join(roles) if roles else "Немає"
            joined_at = target_user.joined_at.strftime("%d %B %Y") if target_user.joined_at else "Невідомо"

            profile_text = f"""```
ПРОФІЛЬ: {target_user.display_name}
Учасник з: {joined_at}

Рівень: {current_level} | XP: {xp} / {xp_needed} ({xp_percent}%)
Voice: {voice_hours} год | Реакцій: {user_data.get("reactions", 0)} | Повідомлень: {user_data.get("messages", 0)}

Ролі: {roles_display}
```"""

            history = user_data.get("history", {})
            days = [datetime.now() - timedelta(days=i) for i in reversed(range(7))]
            labels = [day.strftime('%a') for day in days]
            xp_values = [history.get(day.strftime("%Y-%m-%d"), 0) for day in days]

            plt.figure(figsize=(8, 4))
            plt.plot(labels, xp_values, marker='o', linestyle='-', color='royalblue')
            plt.title('Активність (XP за останні 7 днів)')
            plt.xlabel('День тижня')
            plt.ylabel('Отримано XP')
            plt.grid(True)
            plt.tight_layout()

            file_path = f"profile_graph_{uuid.uuid4().hex}.png"
            plt.savefig(file_path)
            plt.close()

            file = discord.File(file_path, filename="profile_graph.png")
            await interaction.followup.send(content=profile_text, file=file)
            os.remove(file_path)

        except Exception as e:
            await interaction.followup.send(f"⚠️ Помилка при завантаженні профілю: `{e}`")

async def setup(bot):
    await bot.add_cog(ProfileCommands(bot))