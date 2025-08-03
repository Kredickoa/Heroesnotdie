import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class LevelPingCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="levelping", description="Перемкнути пінги при підвищенні рівня")
    async def levelping(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        file_path = "xp_data.json"
        
        # Завантаження даних
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
        else:
            data = {}

        # Створення профілю, якщо нема
        if user_id not in data:
            data[user_id] = {
                "xp": 0,
                "level": 1,
                "allow_level_ping": True
            }

        # Перемикаємо стан
        current_state = data[user_id].get("allow_level_ping", True)
        new_state = not current_state
        data[user_id]["allow_level_ping"] = new_state

        # Зберігаємо
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

        # Відповідь
        if new_state:
            message = "🔔 Пінги при левелапі **увімкнено**."
        else:
            message = "🔕 Пінги при левелапі **вимкнено**."

        await interaction.response.send_message(message, ephemeral=True)

# Реєстрація Cog
async def setup(bot):
    await bot.add_cog(LevelPingCommand(bot))
