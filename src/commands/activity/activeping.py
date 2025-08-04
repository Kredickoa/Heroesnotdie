import discord
from discord.ext import commands, tasks
from modules.db import get_database
from datetime import datetime, timedelta

db = get_database()

class ActivePingChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_active_roles.start()

    def cog_unload(self):
        self.check_active_roles.cancel()

    @tasks.loop(hours=24)
    async def check_active_roles(self):
        # Отримуємо всі гільдії з налаштуваннями activeping
        async for setting in db.settings.find({"active_role_id": {"$exists": True}}):
            guild_id = int(setting["guild_id"])
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            role_id = setting["active_role_id"]
            min_level = setting.get("min_level", 5)
            min_xp_5d = setting.get("min_xp_5d", 500)

            role = guild.get_role(role_id)
            if not role:
                continue

            # Дата 5 днів тому
            cutoff_date = datetime.utcnow() - timedelta(days=5)

            # Перебираємо учасників гільдії
            for member in guild.members:
                if member.bot:
                    continue

                # Отримуємо профіль користувача (припускаємо, що там є рівень і історія XP)
                profile = await db.profiles.find_one({"user_id": str(member.id)})
                if not profile:
                    # Якщо немає профілю, знімаємо роль, якщо є
                    if role in member.roles:
                        try:
                            await member.remove_roles(role, reason="Inactive (no profile)")
                        except Exception:
                            pass
                    continue

                level = profile.get("level", 0)
                xp_history = profile.get("xp_history", [])  # список {"date": ISO, "xp": int}

                # Сумуємо XP за останні 5 днів
                recent_xp = 0
                for entry in xp_history:
                    date_str = entry.get("date")
                    if not date_str:
                        continue
                    date_obj = datetime.fromisoformat(date_str)
                    if date_obj >= cutoff_date:
                        recent_xp += entry.get("xp", 0)

                # Логіка видачі ролі
                has_role = role in member.roles
                if level >= min_level and recent_xp >= min_xp_5d:
                    if not has_role:
                        try:
                            await member.add_roles(role, reason="Active player role assigned")
                        except Exception:
                            pass
                else:
                    if has_role:
                        try:
                            await member.remove_roles(role, reason="Active player role removed (inactive)")
                        except Exception:
                            pass

    @check_active_roles.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(ActivePingChecker(bot))
