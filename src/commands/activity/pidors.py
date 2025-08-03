import discord
from discord import app_commands
from discord.ext import commands
import random
from datetime import datetime, timedelta
from modules.db import get_database

db = get_database()

class PidorCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pidor", description="Рандомно тегнути користувача і отримати +10% HP на 1 годину")
    async def pidor(self, interaction: discord.Interaction):
        user_id = str(interaction.user.id)
        guild_id = interaction.guild.id
        now = datetime.utcnow()

        user_data = await db.users.find_one({"user_id": user_id, "guild_id": guild_id})
        last_used_str = user_data.get("last_pidor_use") if user_data else None

        if last_used_str:
            try:
                last_used = datetime.fromisoformat(last_used_str)
                if now - last_used < timedelta(hours=1):
                    remain = timedelta(hours=1) - (now - last_used)
                    minutes = int(remain.total_seconds() // 60) + 1
                    await interaction.response.send_message(
                        f"⏳ Команда доступна через {minutes} хвилин.", ephemeral=True
                    )
                    return
            except Exception:
                pass

        members = [m for m in interaction.guild.members if not m.bot and not m.system]
        if not members:
            await interaction.response.send_message("Нема користувачів для вибору.", ephemeral=True)
            return

        target = random.choice(members)

        boost_duration = timedelta(hours=1)
        boost_expires = now + boost_duration

        await db.users.update_one(
            {"user_id": user_id, "guild_id": guild_id},
            {
                "$set": {
                    "last_pidor_use": now.isoformat(),
                    "boost": {
                        "type": "hp",
                        "multiplier": 1.10,
                        "expires_at": boost_expires.isoformat()
                    }
                }
            },
            upsert=True,
        )

        await interaction.response.send_message(
            f"🔥 {target.mention} — пидор дня! 🎉\n"
            f"Користувач {interaction.user.mention} отримує +10% HP на 1 годину!",
            ephemeral=False,
        )

async def setup(bot):
    await bot.add_cog(PidorCommand(bot))
