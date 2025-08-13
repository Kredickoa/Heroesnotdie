import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from modules.db import get_database
import asyncio

db = get_database()

class RoleManagementView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Перевіряє чи користувач має право використовувати кнопки"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ У тебе немає прав для управління ролями!", ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji="⬆️", label="Роль за рівнем", style=discord.ButtonStyle.secondary, row=0)
    async def level_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Налаштувати автовидачу ролі за рівнем"""
        await interaction.response.send_message("🎯 **Налаштування автовидачі ролі за рівнем**\n\nВкажи роль (згадування @роль або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо роль
            role_msg = await interaction.client.wait_for('message', check=check)
            role = await self._parse_role(interaction.guild, role_msg.content.strip())
            
            if not role:
                await interaction.followup.send("❌ Роль не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            await interaction.followup.send(f"✅ Роль **{role.name}** знайдено!\n\nТепер вкажи потрібний рівень (1-100):", ephemeral=True)
            
            # Отримуємо рівень
            level_msg = await interaction.client.wait_for('message', check=check)
            
            try:
                level = int(level_msg.content.strip())
                if level <= 0 or level > 100:
                    await interaction.followup.send("❌ Рівень повинен бути від 1 до 100!", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Введи правильне число для рівня!", ephemeral=True)
                return

            # Зберігаємо в БД
            await db.auto_roles.update_one(
                {"guild_id": str(interaction.guild.id), "role_id": str(role.id)},
                {
                    "$set": {
                        "guild_id": str(interaction.guild.id),
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
            
            await interaction.followup.send(f"✅ Налаштовано автовидачу ролі **{role.name}** за **{level} рівень**!", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="⬇️", label="Роль за неактивність", style=discord.ButtonStyle.secondary, row=0)
    async def inactive_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Налаштувати автозняття ролі за неактивність"""
        await interaction.response.send_message("🗑️ **Налаштування автозняття ролі за неактивність**\n\nВкажи роль (згадування @роль або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо роль
            role_msg = await interaction.client.wait_for('message', check=check)
            role = await self._parse_role(interaction.guild, role_msg.content.strip())
            
            if not role:
                await interaction.followup.send("❌ Роль не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            await interaction.followup.send(f"✅ Роль **{role.name}** знайдено!\n\nВкажи кількість днів для перевірки (1-365):", ephemeral=True)
            
            # Отримуємо дні
            days_msg = await interaction.client.wait_for('message', check=check)
            
            try:
                days = int(days_msg.content.strip())
                if days <= 0 or days > 365:
                    await interaction.followup.send("❌ Кількість днів повинна бути від 1 до 365!", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Введи правильне число для днів!", ephemeral=True)
                return

            await interaction.followup.send(f"✅ Період: **{days} днів**\n\nВкажи мінімум XP за цей період:", ephemeral=True)
            
            # Отримуємо XP
            xp_msg = await interaction.client.wait_for('message', check=check)
            
            try:
                min_xp = int(xp_msg.content.strip())
                if min_xp <= 0:
                    await interaction.followup.send("❌ Мінімум XP повинен бути більше 0!", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Введи правильне число для XP!", ephemeral=True)
                return

            # Зберігаємо в БД
            await db.auto_roles.update_one(
                {"guild_id": str(interaction.guild.id), "role_id": str(role.id)},
                {
                    "$set": {
                        "guild_id": str(interaction.guild.id),
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
            
            await interaction.followup.send(f"✅ Налаштовано автозняття ролі **{role.name}** за неактивність ({days} днів, <{min_xp} XP)!", ephemeral=True)

        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="📊", label="Канал звітів", style=discord.ButtonStyle.secondary, row=0)
    async def report_channel(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Встановити канал для звітів"""
        await interaction.response.send_message("📊 **Встановлення каналу для звітів**\n\nВкажи канал (згадування #канал або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо канал
            channel_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            channel = await self._parse_channel(interaction.guild, channel_msg.content.strip())
            
            if not channel or not isinstance(channel, discord.TextChannel):
                await interaction.followup.send("❌ Текстовий канал не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            # Зберігаємо в БД
            await db.guild_settings.update_one(
                {"guild_id": str(interaction.guild.id)},
                {
                    "$set": {
                        "guild_id": str(interaction.guild.id),
                        "report_channel_id": str(channel.id),
                        "updated_by": interaction.user.id,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            await interaction.followup.send(f"✅ Канал для звітів встановлено: {channel.mention}!", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Час очікування вичерпано. Спробуй ще раз.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🗑️", label="Видалити роль", style=discord.ButtonStyle.secondary, row=0)
    async def delete_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Видалити налаштування ролі"""
        await interaction.response.send_message("🗑️ **Видалення налаштувань ролі**\n\nВкажи роль для видалення (згадування @роль або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо роль
            role_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            role = await self._parse_role(interaction.guild, role_msg.content.strip())
            
            if not role:
                await interaction.followup.send("❌ Роль не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            # Видаляємо з БД
            result = await db.auto_roles.delete_one({
                "guild_id": str(interaction.guild.id),
                "role_id": str(role.id)
            })
            
            if result.deleted_count > 0:
                await interaction.followup.send(f"✅ Видалено налаштування для ролі **{role.name}**!", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ Налаштування для ролі **{role.name}** не знайдено!", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Час очікування вичерпано. Спробуй ще раз.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    async def _parse_role(self, guild, role_input):
        """Парсить роль з введення користувача"""
        role = None
        
        if role_input.startswith('<@&') and role_input.endswith('>'):
            role_id = role_input[3:-1]
            try:
                role = guild.get_role(int(role_id))
            except:
                pass
        else:
            try:
                role = guild.get_role(int(role_input))
            except:
                pass
        
        return role

    async def _parse_channel(self, guild, channel_input):
        """Парсить канал з введення користувача"""
        channel = None
        
        if channel_input.startswith('<#') and channel_input.endswith('>'):
            channel_id = channel_input[2:-1]
            try:
                channel = guild.get_channel(int(channel_id))
            except:
                pass
        else:
            try:
                channel = guild.get_channel(int(channel_input))
            except:
                pass
        
        return channel

    @discord.ui.button(emoji="📋", label="Статус системи", style=discord.ButtonStyle.primary, row=1)
    async def system_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показати стан системи"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            auto_roles = await db.auto_roles.find({"guild_id": str(interaction.guild.id), "enabled": True}).to_list(100)
            guild_settings = await db.guild_settings.find_one({"guild_id": str(interaction.guild.id)})
            
            embed = discord.Embed(
                title="⚙️ Стан системи автоматичних ролей",
                color=0x7c7cf0,
                description=""
            )
            
            if not auto_roles:
                embed.add_field(name="❌ Налаштування відсутні", value="Система не налаштована", inline=False)
            else:
                level_roles = []
                inactive_roles = []
                
                for config in auto_roles:
                    role = interaction.guild.get_role(int(config["role_id"]))
                    if not role:
                        continue
                    
                    if config["type"] == "level":
                        users_str = await db.users.find({"guild_id": str(interaction.guild.id)}).to_list(1000)
                        users_int = await db.users.find({"guild_id": interaction.guild.id}).to_list(1000)
                        users = users_str if len(users_str) > 0 else users_int
                        
                        eligible = len([u for u in users if u.get("level", 0) >= config["required_level"]])
                        has_role = len([m for m in interaction.guild.members if role in m.roles])
                        
                        level_roles.append(f"**{role.name}** - Рівень {config['required_level']}\nМає роль: {has_role} | Підходить: {eligible}")
                    elif config["type"] == "inactive":
                        has_role = len([m for m in interaction.guild.members if role in m.roles])
                        inactive_roles.append(f"**{role.name}** - {config['check_days']} днів, {config['min_xp']} XP\nМає роль: {has_role}")
                
                if level_roles:
                    embed.add_field(name="🎯 Автовидача ролей", value="\n\n".join(level_roles), inline=False)
                
                if inactive_roles:
                    embed.add_field(name="🗑️ Автозняття ролей", value="\n\n".join(inactive_roles), inline=False)
            
            # Інформація про канал звітів
            report_channel = None
            if guild_settings and guild_settings.get("report_channel_id"):
                report_channel = interaction.guild.get_channel(int(guild_settings["report_channel_id"]))
            
            channel_status = report_channel.mention if report_channel else "❌ Не встановлено"
            embed.add_field(name="📊 Канал звітів", value=channel_status, inline=False)
            
            embed.set_footer(text=f"Запросив: {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🔄", label="Перевірити зараз", style=discord.ButtonStyle.success, row=1)
    async def check_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Запустити перевірку ролей зараз"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Створюємо екземпляр системи для обробки
            system = AutomatedRoleSystem(interaction.client)
            report = await system._process_guild_roles(interaction.guild)
            
            embed = discord.Embed(
                title="📊 Результат перевірки",
                color=0x00ff00,
                description=""
            )
            
            if report["level_assigned"] > 0:
                level_text = f"**Видано ролей: {report['level_assigned']}**\n"
                level_text += "\n".join([f"• {detail}" for detail in report["level_details"]])
                embed.add_field(name="🎯 Автовидача", value=level_text, inline=False)
            
            if report["inactive_removed"] > 0:
                inactive_text = f"**Знято ролей: {report['inactive_removed']}**\n"
                inactive_text += "\n".join([f"• {detail}" for detail in report["inactive_details"]])
                embed.add_field(name="🗑️ Автозняття", value=inactive_text, inline=False)
                
            if report["level_assigned"] == 0 and report["inactive_removed"] == 0:
                embed.add_field(name="✅ Все актуально", value="Жодних змін не потрібно", inline=False)
            
            embed.set_footer(text=f"Виконав: {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

class AutomatedRoleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.daily_role_check.start()

    def cog_unload(self):
        self.daily_role_check.cancel()

    @app_commands.command(name="role-setup", description="[АДМІН] Налаштування системи автоматичних ролей")
    async def role_setup(self, interaction: discord.Interaction):
        """Панель управління автоматичними ролями"""
        # Перевіряємо права
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ У тебе немає прав для управління ролями!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        embed = discord.Embed(
            title="⚙️ Система автоматичних ролей",
            color=0x7c7cf0,
            description=(
                "Налаштуй автоматичну видачу та зняття ролей на своєму сервері!\n\n"
                "**Доступні функції:**\n"
                "⬆️ **Роль за рівнем** — автоматична видача ролі при досягненні рівня\n"
                "⬇️ **Роль за неактивність** — автоматичне зняття ролі за неактивність\n"
                "📊 **Канал звітів** — встановити канал для щоденних звітів\n"
                "🗑️ **Видалити роль** — видалити налаштування для ролі\n"
                "📋 **Статус системи** — переглянути поточні налаштування\n"
                "🔄 **Перевірити зараз** — запустити перевірку ролей негайно\n\n"
                "💡 **Після натискання кнопки пишіть відповідь у цей же канал!**"
            )
        )
        embed.set_footer(text="Кнопки працюють постійно • Потрібні права: Управління ролями")

        view = RoleManagementView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

    @tasks.loop(hours=24)
    async def daily_role_check(self):
        if db is None:
            return

        for guild in self.bot.guilds:
            try:
                report = await self._process_guild_roles(guild)
                await self._send_daily_report(guild, report)
            except Exception as e:
                print(f"Error processing roles for guild {guild.id}: {e}")

    async def _process_guild_roles(self, guild):
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
                        report["level_details"].append(f"{role.name}: +{assigned}")

                elif config["type"] == "inactive":
                    removed = await self._process_inactive_role(guild, role, config["check_days"], config["min_xp"])
                    report["inactive_removed"] += removed
                    if removed > 0:
                        report["inactive_details"].append(f"{role.name}: -{removed}")
            except Exception as e:
                print(f"Error processing role {role.id}: {e}")

        return report

    async def _process_level_role(self, guild, role, required_level):
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

    async def _process_inactive_role(self, guild, role, days, min_xp):
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

    async def _send_daily_report(self, guild, report):
        guild_settings = await db.guild_settings.find_one({"guild_id": str(guild.id)})
        if not guild_settings or not guild_settings.get("report_channel_id"):
            return

        channel = guild.get_channel(int(guild_settings["report_channel_id"]))
        if not channel:
            return

        if report["level_assigned"] == 0 and report["inactive_removed"] == 0:
            return

        embed = discord.Embed(
            title="📊 Щоденний звіт системи ролей",
            color=0x7c7cf0,
            timestamp=datetime.utcnow()
        )

        if report["level_assigned"] > 0:
            level_text = f"**Видано ролей: {report['level_assigned']}**\n"
            level_text += "\n".join([f"• {detail}" for detail in report["level_details"]])
            embed.add_field(name="🎯 Автовидача", value=level_text, inline=False)

        if report["inactive_removed"] > 0:
            inactive_text = f"**Знято ролей: {report['inactive_removed']}**\n"
            inactive_text += "\n".join([f"• {detail}" for detail in report["inactive_details"]])
            embed.add_field(name="🗑️ Автозняття", value=inactive_text, inline=False)

        embed.set_footer(text="Автоматична перевірка системи ролей")

        try:
            await channel.send(embed=embed)
        except:
            pass

    @daily_role_check.before_loop
    async def before_daily_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AutomatedRoleSystem(bot))