import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from modules.db import get_database

db = get_database()

class AutomatedRoleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_role_check.start()  # Запускаємо автоматичну перевірку

    def cog_unload(self):
        self.daily_role_check.cancel()

    @app_commands.command(name="autoroles", description="Налаштування автоматичного управління ролями")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(
        дія="Що налаштувати",
        role="Роль для управління",
        значення="Рівень або кількість днів",
        мін_xp="Мінімум XP за період (для неактивності)",
        канал="Канал для звітів (опціонально)"
    )
    @app_commands.choices(дія=[
        app_commands.Choice(name="Налаштувати автовидачу за рівнем", value="setup_level"),
        app_commands.Choice(name="Налаштувати автозняття за неактивність", value="setup_inactive"),
        app_commands.Choice(name="Встановити канал для звітів", value="set_channel"),
        app_commands.Choice(name="Показати поточні налаштування", value="show_config"),
        app_commands.Choice(name="Видалити налаштування ролі", value="remove_config"),
        app_commands.Choice(name="Запустити перевірку зараз", value="run_now")
    ])
    async def autoroles(self, interaction: discord.Interaction, дія: app_commands.Choice[str], 
                       role: discord.Role = None, значення: int = 0, мін_xp: int = 0, 
                       канал: discord.TextChannel = None):
        await interaction.response.defer(ephemeral=True)

        if db is None:
            await interaction.followup.send("❌ Помилка: не вдалося підключитися до бази даних!")
            return

        guild = interaction.guild

        try:
            if дія.value == "setup_level":
                if not role or значення <= 0:
                    await interaction.followup.send("❌ Потрібно вказати роль і рівень!")
                    return
                await self._setup_level_role(interaction, guild, role, значення)

            elif дія.value == "setup_inactive":
                if not role or значення <= 0 or мін_xp <= 0:
                    await interaction.followup.send("❌ Потрібно вказати роль, дні і мінімум XP!")
                    return
                await self._setup_inactive_role(interaction, guild, role, значення, мін_xp)

            elif дія.value == "set_channel":
                if not канал:
                    await interaction.followup.send("❌ Потрібно вказати канал!")
                    return
                await self._set_report_channel(interaction, guild, канал)

            elif дія.value == "show_config":
                await self._show_config(interaction, guild)

            elif дія.value == "remove_config":
                if not role:
                    await interaction.followup.send("❌ Потрібно вказати роль!")
                    return
                await self._remove_config(interaction, guild, role)

            elif дія.value == "run_now":
                await self._run_check_now(interaction, guild)

        except Exception as e:
            await interaction.followup.send(f"❌ Сталася помилка: {str(e)}")

    async def _setup_level_role(self, interaction, guild, role, level):
        """Налаштування автовидачі ролі за рівнем"""
        await db.auto_roles.update_one(
            {"guild_id": str(guild.id), "role_id": str(role.id)},
            {
                "$set": {
                    "guild_id": str(guild.id),
                    "role_id": str(role.id),
                    "type": "level",
                    "required_level": level,
                    "enabled": True,
                    "created_by": interaction.user.id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        result = f"```\n✅ АВТОВИДАЧА РОЛІ НАЛАШТОВАНА\n\n"
        result += f"Роль: {role.name}\n"
        result += f"Умова: Рівень {level} і вище\n"
        result += f"Статус: Активна\n\n"
        result += f"Роль буде видана всім підходящим користувачам\nпри наступній перевірці\n```"

        await interaction.followup.send(result)

    async def _setup_inactive_role(self, interaction, guild, role, days, min_xp):
        """Налаштування автозняття ролі за неактивність"""
        await db.auto_roles.update_one(
            {"guild_id": str(guild.id), "role_id": str(role.id)},
            {
                "$set": {
                    "guild_id": str(guild.id),
                    "role_id": str(role.id),
                    "type": "inactive",
                    "check_days": days,
                    "min_xp": min_xp,
                    "enabled": True,
                    "created_by": interaction.user.id,
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        result = f"```\n🗑️ АВТОЗНЯТТЯ РОЛІ НАЛАШТОВАНО\n\n"
        result += f"Роль: {role.name}\n"
        result += f"Період: {days} днів\n"
        result += f"Мін. XP: {min_xp}\n"
        result += f"Статус: Активна\n\n"
        result += f"Роль буде знята у користувачів, які не набрали\n{min_xp} XP за останні {days} днів\n```"

        await interaction.followup.send(result)

    async def _set_report_channel(self, interaction, guild, channel):
        """Налаштування каналу для звітів"""
        await db.guild_settings.update_one(
            {"guild_id": str(guild.id)},
            {
                "$set": {
                    "guild_id": str(guild.id),
                    "report_channel_id": str(channel.id),
                    "updated_by": interaction.user.id,
                    "updated_at": datetime.utcnow()
                }
            },
            upsert=True
        )

        result = f"```\n📊 КАНАЛ ДЛЯ ЗВІТІВ ВСТАНОВЛЕНО\n\n"
        result += f"Канал: #{channel.name}\n\n"
        result += f"Автоматичні звіти будуть надсилатися:\n"
        result += f"• Щоденні звіти про видачу ролей\n"
        result += f"• Звіти про зняття ролей\n"
        result += f"• Статистика змін\n```"

        await interaction.followup.send(result)

    async def _show_config(self, interaction, guild):
        """Показати поточні налаштування"""
        auto_roles = await db.auto_roles.find({"guild_id": str(guild.id), "enabled": True}).to_list(100)
        guild_settings = await db.guild_settings.find_one({"guild_id": str(guild.id)})

        result = "```\n⚙️ НАЛАШТУВАННЯ АВТОМАТИЧНИХ РОЛЕЙ\n\n"

        if not auto_roles:
            result += "❌ Немає активних налаштувань\n"
        else:
            level_roles = []
            inactive_roles = []

            for config in auto_roles:
                role = guild.get_role(int(config["role_id"]))
                if not role:
                    continue

                if config["type"] == "level":
                    level_roles.append(f"  • {role.name:<20} | Рівень: {config['required_level']}")
                elif config["type"] == "inactive":
                    inactive_roles.append(f"  • {role.name:<20} | {config['check_days']} днів, {config['min_xp']} XP")

            if level_roles:
                result += "🎯 АВТОВИДАЧА ЗА РІВНЕМ:\n"
                result += "\n".join(level_roles) + "\n\n"

            if inactive_roles:
                result += "🗑️ АВТОЗНЯТТЯ ЗА НЕАКТИВНІСТЬ:\n"
                result += "\n".join(inactive_roles) + "\n\n"

        # Канал для звітів
        report_channel = None
        if guild_settings and guild_settings.get("report_channel_id"):
            report_channel = guild.get_channel(int(guild_settings["report_channel_id"]))

        result += f"📊 КАНАЛ ДЛЯ ЗВІТІВ:\n"
        result += f"  {report_channel.name if report_channel else '❌ Не налаштовано'}\n```"

        await interaction.followup.send(result)

    async def _remove_config(self, interaction, guild, role):
        """Видалити налаштування ролі"""
        result_db = await db.auto_roles.delete_one({
            "guild_id": str(guild.id),
            "role_id": str(role.id)
        })

        if result_db.deleted_count > 0:
            result = f"```\n✅ НАЛАШТУВАННЯ ВИДАЛЕНО\n\n"
            result += f"Роль: {role.name}\n"
            result += f"Автоматичне управління відключено\n```"
        else:
            result = f"```\n❌ НАЛАШТУВАННЯ НЕ ЗНАЙДЕНО\n\n"
            result += f"Роль: {role.name}\n"
            result += f"Немає активних налаштувань для цієї ролі\n```"

        await interaction.followup.send(result)

    async def _run_check_now(self, interaction, guild):
        """Запустити перевірку зараз"""
        await interaction.followup.send("🔄 Запускаю перевірку ролей...")
        
        report = await self._process_guild_roles(guild)
        
        result = f"```\n📊 РЕЗУЛЬТАТ ПЕРЕВІРКИ РОЛЕЙ\n\n"
        
        if report["level_assigned"] > 0:
            result += f"🎯 Видано ролей за рівнем: {report['level_assigned']}\n"
            if report["level_details"]:
                for detail in report["level_details"]:
                    result += f"   {detail}\n"
                result += "\n"
        
        if report["inactive_removed"] > 0:
            result += f"🗑️ Знято ролей за неактивність: {report['inactive_removed']}\n"
            if report["inactive_details"]:
                for detail in report["inactive_details"]:
                    result += f"   {detail}\n"
                result += "\n"
            
        if report["level_assigned"] == 0 and report["inactive_removed"] == 0:
            result += "✅ Всі ролі актуальні, змін не потрібно\n\n"

        result += f"Виконав: {interaction.user.display_name}\n```"
        
        await interaction.edit_original_response(content=result)

    @tasks.loop(hours=24)  # Перевірка щодня
    async def daily_role_check(self):
        """Щоденна автоматична перевірка ролей"""
        db = get_database()
        if db is None:
            return

        for guild in self.bot.guilds:
            try:
                report = await self._process_guild_roles(guild, db)
                await self._send_daily_report(guild, db, report)
            except Exception as e:
                print(f"Error processing roles for guild {guild.id}: {e}")

    async def _process_guild_roles(self, guild):
        """Обробка ролей для гільдії"""
        auto_roles = await db.auto_roles.find({"guild_id": str(guild.id), "enabled": True}).to_list(100)
        
        report = {
            "level_assigned": 0,
            "inactive_removed": 0,
            "level_details": [],
            "inactive_details": []
        }

        for config in auto_roles:
            role = guild.get_role(int(config["role_id"]))
            if not role or role.position >= guild.me.top_role.position:
                continue

            try:
                if config["type"] == "level":
                    assigned = await self._process_level_role(guild, role, config["required_level"])
                    report["level_assigned"] += assigned
                    if assigned > 0:
                        report["level_details"].append(f"• {role.name}: +{assigned}")

                elif config["type"] == "inactive":
                    removed = await self._process_inactive_role(guild, role, config["check_days"], config["min_xp"])
                    report["inactive_removed"] += removed
                    if removed > 0:
                        report["inactive_details"].append(f"• {role.name}: -{removed}")
            except Exception as e:
                print(f"Error processing role {role.id}: {e}")

        return report

    async def _process_level_role(self, guild, role, required_level):
        """Обробка ролей за рівнем"""
        users_str = await db.users.find({"guild_id": str(guild.id)}).to_list(1000)
        users_int = await db.users.find({"guild_id": guild.id}).to_list(1000)
        users = users_str if len(users_str) > 0 else users_int

        eligible_users = [user for user in users if user.get("level", 0) >= required_level]
        assigned_count = 0

        for user_data in eligible_users:
            user_id = user_data.get("user_id")
            if isinstance(user_id, str):
                user_id = int(user_id)

            member = guild.get_member(user_id)
            if member and role not in member.roles:
                try:
                    await member.add_roles(role, reason=f"Автоматична видача за рівень {required_level}")
                    assigned_count += 1
                except:
                    pass

        return assigned_count

    async def _process_inactive_role(self, guild, db, role, days, min_xp):
        """Обробка зняття ролей за неактивність"""
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_date_str = cutoff_date.strftime("%Y-%m-%d")
        
        members_with_role = [member for member in guild.members if role in member.roles]
        removed_count = 0

        for member in members_with_role:
            user_data = await db.users.find_one({
                "$or": [
                    {"guild_id": str(guild.id), "user_id": member.id},
                    {"guild_id": guild.id, "user_id": member.id},
                    {"guild_id": str(guild.id), "user_id": str(member.id)},
                    {"guild_id": guild.id, "user_id": str(member.id)}
                ]
            })

            should_remove = False
            if not user_data:
                should_remove = True
            else:
                history = user_data.get("history", {})
                recent_xp = sum(
                    day_data.get("xp_gained", 0)
                    for date_str, day_data in history.items()
                    if date_str >= cutoff_date_str
                )
                if recent_xp < min_xp:
                    should_remove = True

            if should_remove:
                try:
                    await member.remove_roles(role, reason=f"Автоматичне зняття за неактивність ({days} днів, <{min_xp} XP)")
                    removed_count += 1
                except:
                    pass

        return removed_count

    async def _send_daily_report(self, guild, db, report):
        """Надіслати щоденний звіт"""
        guild_settings = await db.guild_settings.find_one({"guild_id": str(guild.id)})
        if not guild_settings or not guild_settings.get("report_channel_id"):
            return

        channel = guild.get_channel(int(guild_settings["report_channel_id"]))
        if not channel:
            return

        # Надсилаємо звіт тільки якщо були зміни
        if report["level_assigned"] == 0 and report["inactive_removed"] == 0:
            return

        result = f"```\n📊 ЩОДЕННИЙ ЗВІТ АВТОМАТИЧНИХ РОЛЕЙ\n\n"

        if report["level_assigned"] > 0:
            result += f"🎯 ВИДАНО РОЛЕЙ ЗА РІВНЕМ: {report['level_assigned']}\n"
            for detail in report["level_details"]:
                result += f"   {detail}\n"
            result += "\n"

        if report["inactive_removed"] > 0:
            result += f"🗑️ ЗНЯТО РОЛЕЙ ЗА НЕАКТИВНІСТЬ: {report['inactive_removed']}\n"
            for detail in report["inactive_details"]:
                result += f"   {detail}\n"
            result += "\n"

        result += f"🤖 Автоматична перевірка\n"
        result += f"Час: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n```"

        try:
            await channel.send(result)
        except:
            pass

    @daily_role_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutomatedRoleSystem(bot))