import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta
from modules.db import get_database
import asyncio

db = get_database()

class WeeklyRoleView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Перевіряє чи користувач має право використовувати кнопки"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ У тебе немає прав для управління ролями!", ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji="📝", label="Роль за топ чату", style=discord.ButtonStyle.primary, row=0)
    async def chat_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Налаштувати роль за топ активність в чаті"""
        await interaction.response.send_message("📝 **Налаштування ролі за топ активність в чаті**\n\nВкажи роль (згадування @роль або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо роль
            role_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            role = await self._parse_role(interaction.guild, role_msg.content.strip())
            
            if not role:
                await interaction.followup.send("❌ Роль не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            await interaction.followup.send(f"✅ Роль **{role.name}** знайдено!\n\nСкільки людей має отримати цю роль? (топ 1-50):", ephemeral=True)
            
            # Отримуємо кількість топу
            top_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            try:
                top_count = int(top_msg.content.strip())
                if top_count <= 0 or top_count > 50:
                    await interaction.followup.send("❌ Кількість повинна бути від 1 до 50!", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Введи правильне число!", ephemeral=True)
                return

            # Зберігаємо в БД
            await db.weekly_roles.update_one(
                {"guild_id": str(interaction.guild.id), "role_id": str(role.id)},
                {
                    "$set": {
                        "guild_id": str(interaction.guild.id),
                        "role_id": str(role.id),
                        "type": "chat",
                        "top_count": top_count,
                        "enabled": True,
                        "created_by": interaction.user.id,
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            await interaction.followup.send(f"✅ Налаштовано роль **{role.name}** для топ {top_count} активних в чаті!", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Час очікування вичерпано. Спробуй ще раз.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🎤", label="Роль за топ войсу", style=discord.ButtonStyle.primary, row=0)
    async def voice_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Налаштувати роль за топ активність в войсі"""
        await interaction.response.send_message("🎤 **Налаштування ролі за топ активність в войсі**\n\nВкажи роль (згадування @роль або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо роль
            role_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            role = await self._parse_role(interaction.guild, role_msg.content.strip())
            
            if not role:
                await interaction.followup.send("❌ Роль не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            await interaction.followup.send(f"✅ Роль **{role.name}** знайдено!\n\nСкільки людей має отримати цю роль? (топ 1-50):", ephemeral=True)
            
            # Отримуємо кількість топу
            top_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            try:
                top_count = int(top_msg.content.strip())
                if top_count <= 0 or top_count > 50:
                    await interaction.followup.send("❌ Кількість повинна бути від 1 до 50!", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Введи правильне число!", ephemeral=True)
                return

            # Зберігаємо в БД
            await db.weekly_roles.update_one(
                {"guild_id": str(interaction.guild.id), "role_id": str(role.id)},
                {
                    "$set": {
                        "guild_id": str(interaction.guild.id),
                        "role_id": str(role.id),
                        "type": "voice",
                        "top_count": top_count,
                        "enabled": True,
                        "created_by": interaction.user.id,
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            await interaction.followup.send(f"✅ Налаштовано роль **{role.name}** для топ {top_count} активних в войсі!", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Час очікування вichерпано. Спробуй ще раз.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🏆", label="Роль за загальний топ", style=discord.ButtonStyle.primary, row=0)
    async def combined_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Налаштувати роль за топ загальної активності"""
        await interaction.response.send_message("🏆 **Налаштування ролі за топ загальної активності**\n\nВкажи роль (згадування @роль або ID):", ephemeral=True)
        
        def check(message):
            return message.author.id == interaction.user.id and message.channel.id == interaction.channel.id

        try:
            # Отримуємо роль
            role_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            role = await self._parse_role(interaction.guild, role_msg.content.strip())
            
            if not role:
                await interaction.followup.send("❌ Роль не знайдено! Спробуй ще раз.", ephemeral=True)
                return

            await interaction.followup.send(f"✅ Роль **{role.name}** знайдено!\n\nСкільки людей має отримати цю роль? (топ 1-50):", ephemeral=True)
            
            # Отримуємо кількість топу
            top_msg = await interaction.client.wait_for('message', check=check, timeout=60.0)
            
            try:
                top_count = int(top_msg.content.strip())
                if top_count <= 0 or top_count > 50:
                    await interaction.followup.send("❌ Кількість повинна бути від 1 до 50!", ephemeral=True)
                    return
            except ValueError:
                await interaction.followup.send("❌ Введи правильне число!", ephemeral=True)
                return

            # Зберігаємо в БД
            await db.weekly_roles.update_one(
                {"guild_id": str(interaction.guild.id), "role_id": str(role.id)},
                {
                    "$set": {
                        "guild_id": str(interaction.guild.id),
                        "role_id": str(role.id),
                        "type": "combined",
                        "top_count": top_count,
                        "enabled": True,
                        "created_by": interaction.user.id,
                        "created_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            await interaction.followup.send(f"✅ Налаштовано роль **{role.name}** для топ {top_count} найактивніших загалом!", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Час очікування вичерпано. Спробуй ще раз.", ephemeral=True)
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
                        "weekly_report_channel_id": str(channel.id),
                        "updated_by": interaction.user.id,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            
            await interaction.followup.send(f"✅ Канал для щотижневих звітів встановлено: {channel.mention}!", ephemeral=True)

        except asyncio.TimeoutError:
            await interaction.followup.send("⏰ Час очікування вичерпано. Спробуй ще раз.", ephemeral=True)
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🗑️", label="Видалити роль", style=discord.ButtonStyle.danger, row=1)
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
            result = await db.weekly_roles.delete_one({
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

    @discord.ui.button(emoji="📋", label="Статус системи", style=discord.ButtonStyle.success, row=1)
    async def system_status(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Показати стан системи"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            weekly_roles = await db.weekly_roles.find({"guild_id": str(interaction.guild.id), "enabled": True}).to_list(100)
            guild_settings = await db.guild_settings.find_one({"guild_id": str(interaction.guild.id)})
            
            embed = discord.Embed(
                title="⚙️ Стан системи щотижневих ролей",
                color=0x7c7cf0,
                description=""
            )
            
            if not weekly_roles:
                embed.add_field(name="❌ Налаштування відсутні", value="Система не налаштована", inline=False)
            else:
                chat_roles = []
                voice_roles = []
                combined_roles = []
                
                for config in weekly_roles:
                    role = interaction.guild.get_role(int(config["role_id"]))
                    if not role:
                        continue
                    
                    has_role = len([m for m in interaction.guild.members if role in m.roles])
                    role_info = f"**{role.name}** - топ {config['top_count']}\nМає роль: {has_role} осіб"
                    
                    if config["type"] == "chat":
                        chat_roles.append(role_info)
                    elif config["type"] == "voice":
                        voice_roles.append(role_info)
                    elif config["type"] == "combined":
                        combined_roles.append(role_info)
                
                if chat_roles:
                    embed.add_field(name="📝 Ролі за топ чату", value="\n\n".join(chat_roles), inline=False)
                
                if voice_roles:
                    embed.add_field(name="🎤 Ролі за топ войсу", value="\n\n".join(voice_roles), inline=False)
                    
                if combined_roles:
                    embed.add_field(name="🏆 Ролі за загальний топ", value="\n\n".join(combined_roles), inline=False)
            
            # Інформація про канал звітів
            report_channel = None
            if guild_settings and guild_settings.get("weekly_report_channel_id"):
                report_channel = interaction.guild.get_channel(int(guild_settings["weekly_report_channel_id"]))
            
            channel_status = report_channel.mention if report_channel else "❌ Не встановлено"
            embed.add_field(name="📊 Канал звітів", value=channel_status, inline=False)
            
            # Інформація про наступне оновлення
            now = datetime.now()
            days_until_monday = (7 - now.weekday()) % 7
            if days_until_monday == 0:
                days_until_monday = 7
            next_update = now + timedelta(days=days_until_monday)
            embed.add_field(name="🕐 Наступне оновлення", value=f"<t:{int(next_update.timestamp())}:R>", inline=False)
            
            embed.set_footer(text=f"Запросив: {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}", ephemeral=True)

    @discord.ui.button(emoji="🔄", label="Оновити зараз", style=discord.ButtonStyle.success, row=1)
    async def update_now(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Запустити оновлення ролей зараз"""
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Створюємо екземпляр системи для обробки
            system = WeeklyRoleSystem(interaction.client)
            report = await system._process_guild_weekly_roles(interaction.guild)
            
            embed = discord.Embed(
                title="📊 Результат оновлення ролей",
                color=0x00ff00,
                description=""
            )
            
            total_assigned = sum(report["assigned"].values())
            total_removed = sum(report["removed"].values())
            
            if total_assigned > 0:
                assigned_text = f"**Всього видано: {total_assigned}**\n"
                for role_name, count in report["assigned"].items():
                    if count > 0:
                        assigned_text += f"• {role_name}: +{count}\n"
                embed.add_field(name="✅ Видано ролей", value=assigned_text, inline=False)
            
            if total_removed > 0:
                removed_text = f"**Всього знято: {total_removed}**\n"
                for role_name, count in report["removed"].items():
                    if count > 0:
                        removed_text += f"• {role_name}: -{count}\n"
                embed.add_field(name="❌ Знято ролей", value=removed_text, inline=False)
                
            if total_assigned == 0 and total_removed == 0:
                embed.add_field(name="✅ Все актуально", value="Жодних змін не потрібно", inline=False)
            
            embed.set_footer(text=f"Виконав: {interaction.user.display_name}")
            
            await interaction.followup.send(embed=embed, ephemeral=True)
            
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

class WeeklyRoleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.weekly_role_update.start()

    def cog_unload(self):
        self.weekly_role_update.cancel()

    @app_commands.command(name="weekly-setup", description="[АДМІН] Налаштування системи щотижневих ролей")
    async def weekly_setup(self, interaction: discord.Interaction):
        """Панель управління щотижневими ролями"""
        # Перевіряємо права
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ У тебе немає прав для управління ролями!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=False)

        embed = discord.Embed(
            title="🏆 Система щотижневих ролей",
            color=0x7c7cf0,
            description=(
                "Налаштуй автоматичну видачу ролей за щотижневу активність!\n\n"
                "**Доступні функції:**\n"
                "📝 **Роль за топ чату** — для найактивніших в чаті\n"
                "🎤 **Роль за топ войсу** — для найактивніших в голосових каналах\n"
                "🏆 **Роль за загальний топ** — для найактивніших загалом\n"
                "📊 **Канал звітів** — встановити канал для щотижневих звітів\n"
                "🗑️ **Видалити роль** — видалити налаштування для ролі\n"
                "📋 **Статус системи** — переглянути поточні налаштування\n"
                "🔄 **Оновити зараз** — запустити оновлення ролей негайно\n\n"
                "💡 **Ролі оновлюються щопонеділка о 00:00**\n"
                "📈 **Активність рахується за останні 7 днів**"
            )
        )
        embed.set_footer(text="Кнопки працюють постійно • Потрібні права: Управління ролями")

        view = WeeklyRoleView()
        await interaction.followup.send(embed=embed, view=view, ephemeral=False)

    @tasks.loop(time=discord.utils.utcnow().replace(hour=0, minute=0, second=0, microsecond=0))
    async def weekly_role_update(self):
        """Щотижневе оновлення ролей (кожного понеділка)"""
        # Перевіряємо чи сьогодні понеділок
        if datetime.now().weekday() != 0:
            return

        if db is None:
            return

        for guild in self.bot.guilds:
            try:
                report = await self._process_guild_weekly_roles(guild)
                await self._send_weekly_report(guild, report)
            except Exception as e:
                print(f"Error processing weekly roles for guild {guild.id}: {e}")

    async def _process_guild_weekly_roles(self, guild):
        """Обробляє щотижневі ролі для сервера"""
        weekly_roles = await db.weekly_roles.find({"guild_id": str(guild.id), "enabled": True}).to_list(100)
        
        report = {
            "assigned": {},
            "removed": {}
        }

        # Отримуємо дані активності за останні 7 днів
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        date_range = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(7)]

        for config in weekly_roles:
            role = guild.get_role(int(config["role_id"]))
            if not role or role.position >= guild.me.top_role.position:
                continue

            try:
                # Отримуємо топ користувачів
                top_users = await self._get_top_users(guild, config["type"], config["top_count"], date_range)
                
                # Видаємо/знімаємо ролі
                assigned, removed = await self._update_role_assignments(guild, role, top_users)
                
                report["assigned"][role.name] = assigned
                report["removed"][role.name] = removed
                
            except Exception as e:
                print(f"Error processing role {role.id}: {e}")

        return report

    async def _get_top_users(self, guild, activity_type, top_count, date_range):
        """Отримує топ користувачів за активністю"""
        # Отримуємо всіх користувачів сервера
        users_str = await db.users.find({"guild_id": str(guild.id)}).to_list(10000)
        users_int = await db.users.find({"guild_id": guild.id}).to_list(10000)
        users = users_str if len(users_str) > 0 else users_int

        user_activity = []

        for user_data in users:
            user_id = user_data.get("user_id")
            if isinstance(user_id, str):
                try:
                    user_id = int(user_id)
                except:
                    continue

            member = guild.get_member(user_id)
            if not member or member.bot:
                continue

            history = user_data.get("history", {})
            
            if activity_type == "chat":
                # Підраховуємо повідомлення за тиждень (10 XP за повідомлення)
                weekly_messages = 0
                for date_str in date_range:
                    daily_xp = history.get(date_str, 0)
                    # Приблизно підраховуємо повідомлення (не точно, але орієнтовно)
                    # XP може йти з різних джерел, тому це приблизна оцінка
                    weekly_messages += daily_xp // 10
                
                user_activity.append((user_id, weekly_messages))
                
            elif activity_type == "voice":
                # Підраховуємо час в войсі за тиждень (5 XP за хвилину)
                weekly_voice = 0
                for date_str in date_range:
                    daily_xp = history.get(date_str, 0)
                    # Приблизно підраховуємо хвилини войсу
                    weekly_voice += daily_xp // 5
                
                user_activity.append((user_id, weekly_voice))
                
            elif activity_type == "combined":
                # Підраховуємо загальний XP за тиждень
                weekly_xp = 0
                for date_str in date_range:
                    weekly_xp += history.get(date_str, 0)
                
                user_activity.append((user_id, weekly_xp))

        # Сортуємо за активністю та беремо топ
        user_activity.sort(key=lambda x: x[1], reverse=True)
        top_users = [user_id for user_id, activity in user_activity[:top_count] if activity > 0]

        return top_users

    async def _update_role_assignments(self, guild, role, top_users):
        """Оновлює призначення ролей"""
        assigned_count = 0
        removed_count = 0

        # Отримуємо всіх учасників, які зараз мають цю роль
        current_role_members = [member.id for member in guild.members if role in member.roles]

        # Знімаємо роль у тих, хто не в топі
        for member_id in current_role_members:
            if member_id not in top_users:
                member = guild.get_member(member_id)
                if member:
                    try:
                        await member.remove_roles(role, reason="Щотижневе оновлення ролей - не в топі")
                        removed_count += 1
                    except:
                        pass

        # Видаємо роль тим, хто в топі але не має її
        for user_id in top_users:
            if user_id not in current_role_members:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.add_roles(role, reason="Щотижневе оновлення ролей - в топі")
                        assigned_count += 1
                    except:
                        pass

        return assigned_count, removed_count

    async def _send_weekly_report(self, guild, report):
        """Відправляє щотижневий звіт"""
        guild_settings = await db.guild_settings.find_one({"guild_id": str(guild.id)})
        if not guild_settings or not guild_settings.get("weekly_report_channel_id"):
            return

        channel = guild.get_channel(int(guild_settings["weekly_report_channel_id"]))
        if not channel:
            return

        total_assigned = sum(report["assigned"].values())
        total_removed = sum(report["removed"].values())

        # Якщо немає змін, не відправляємо звіт
        if total_assigned == 0 and total_removed == 0:
            return

        embed = discord.Embed(
            title="🏆 Щотижневий звіт системи ролей",
            color=0x7c7cf0,
            timestamp=datetime.utcnow(),
            description="Результати оновлення ролей за минулий тиждень"
        )

        if total_assigned > 0:
            assigned_text = f"**Всього видано: {total_assigned}**\n"
            for role_name, count in report["assigned"].items():
                if count > 0:
                    assigned_text += f"• {role_name}: +{count}\n"
            embed.add_field(name="✅ Видано ролей", value=assigned_text, inline=False)

        if total_removed > 0:
            removed_text = f"**Всього знято: {total_removed}**\n"
            for role_name, count in report["removed"].items():
                if count > 0:
                    removed_text += f"• {role_name}: -{count}\n"
            embed.add_field(name="❌ Знято ролей", value=removed_text, inline=False)

        embed.add_field(
            name="📅 Наступне оновлення", 
            value="<t:" + str(int((datetime.now() + timedelta(days=7)).timestamp())) + ":R>", 
            inline=False
        )
        embed.set_footer(text="Автоматичне щотижневе оновлення ролей")

        try:
            await channel.send(embed=embed)
        except:
            pass

    @weekly_role_update.before_loop
    async def before_weekly_update(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(WeeklyRoleSystem(bot))