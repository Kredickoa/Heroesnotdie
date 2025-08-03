import discord
from discord import app_commands
from discord.ext import commands
import json
import os

class LevelPing(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="levelping", description="Увімкнути або вимкнути пінг при підвищенні рівня")
    @app_commands.describe(state="on або off")
    async def levelping(self, interaction: discord.Interaction, state: str):
        user_id = str(interaction.user.id)
        file_path = "xp_data.json"

        # завантажити або створити файл
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                data = json.load(f)
        else:
            data = {}

        if user_id not in data:
            data[user_id] = {
                "xp": 0,
                "level": 1,
                "allow_level_ping": True
            }

        if state.lower() == "off":
            data[user_id]["allow_level_ping"] = False
            msg = "🔕 Ви вимкнули пінги при підвищенні рівня."
        elif state.lower() == "on":
            data[user_id]["allow_level_ping"] = True
            msg = "🔔 Ви увімкнули пінги при підвищенні рівня."
        else:
            await interaction.response.send_message("❗ Використовуйте або `on`, або `off`.", ephemeral=True)
            return

        # зберегти
        with open(file_path, "w") as f:
            json.dump(data, f, indent=4)

        await interaction.response.send_message(msg, ephemeral=True)

# обов'язково setup
async def setup(bot):
    await bot.add_cog(LevelPing(bot))
