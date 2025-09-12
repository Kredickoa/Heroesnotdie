import discord
from discord import app_commands
from discord.ext import commands, tasks
from datetime import datetime, timedelta, time
from typing import List, Optional
from modules.db import get_database
import asyncio
import math

db = get_database()

class ActivityType:
    CHAT = "chat"
    VOICE = "voice" 
    COMBINED = "combined"

class RoleSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild):
        super().__init__(timeout=300)
        self.guild = guild
        self.selected_roles: List[discord.Role] = []
        self.current_page = 0
        self.roles_per_page = 25
        
        # Фільтруємо всі доступні ролі
        self.available_roles = [
            role for role in self.guild.roles 
            if role != self.guild.default_role 
            and not role.managed 
            and role.position < self.guild.me.top_role.position
        ]
        
        self.total_pages = math.ceil(len(self.available_roles) / self.roles_per_page)
        self.update_select()

    def get_page_roles(self):
        start = self.current_page * self.roles_per_page
        end = start + self.roles_per_page
        return self.available_roles[start:end]

    def update_select(self):
        # Очищуємо всі елементи
        self.clear_items()
        
        page_roles = self.get_page_roles()
        
        if page_roles:
            select = RoleSelect(page_roles, self.selected_roles)
            self.add_item(select)
        
        # Кнопки навігації по сторінках
        if self.total_pages > 1:
            prev_btn = discord.ui.Button(
                label="◀ Попередня",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page == 0,
                row=1
            )
            prev_btn.callback = self.previous_page
            self.add_item(prev_btn)
            
            page_info_btn = discord.ui.Button(
                label=f"Сторінка {self.current_page + 1}/{self.total_pages}",
                style=discord.ButtonStyle.secondary,
                disabled=True,
                row=1
            )
            self.add_item(page_info_btn)
            
            next_btn = discord.ui.Button(
                label="Наступна ▶",
                style=discord.ButtonStyle.secondary,
                disabled=self.current_page >= self.total_pages - 1,
                row=1
            )
            next_btn.callback = self.next_page
            self.add_item(next_btn)
        
        # Кнопка вибрати всі ролі на поточній сторінці
        if page_roles:
            select_all_btn = discord.ui.Button(
                label=f"Вибрати всі на сторінці ({len(page_roles)})",
                style=discord.ButtonStyle.primary,
                emoji="☑️",
                row=2
            )
            select_all_btn.callback = self.select_all_on_page
            self.add_item(select_all_btn)
        
        # Кнопка очистити всі обрані ролі
        if self.selected_roles:
            clear_all_btn = discord.ui.Button(
                label=f"Очистити всі ({len(self.selected_roles)})",
                style=discord.ButtonStyle.danger,
                emoji="🗑️",
                row=2
            )
            clear_all_btn.callback = self.clear_all
            self.add_item(clear_all_btn)
        
        # Кнопка продовження
        if self.selected_roles:
            continue_btn = discord.ui.Button(
                label=f"Продовжити з {len(self.selected_roles)} роллю/ями",
                style=discord.ButtonStyle.green,
                emoji="✅",
                row=3
            )
            continue_btn.callback = self.continue_setup
            self.add_item(continue_btn)

    async def previous_page(self, interaction: discord.Interaction):
        if self.current_page > 0:
            self.current_page -= 1
            self.update_select()
            
            embed = discord.Embed(
                title="🏆 Крок 1: Вибір ролей",
                color=0x7c7cf0,
                description=f"**Сторінка {self.current_page + 1}/{self.total_pages}**\n"
                           f"**Обрано ролей:** {len(self.selected_roles)}\n" + 
                           (", ".join([role.mention for role in self.selected_roles[:10]]) + 
                            (f" і ще {len(self.selected_roles) - 10}..." if len(self.selected_roles) > 10 else "") 
                            if self.selected_roles else "Жодної ролі не обрано")
            )
            
            await interaction.response.edit_message(embed=embed, view=self)

    async def next_page(self, interaction: discord.Interaction):
        if self.current_page < self.total_pages - 1:
            self.current_page += 1
            self.update_select()
            
            embed = discord.Embed(
                title="🏆 Крок 1: Вибір ролей",
                color=0x7c7cf0,
                description=f"**Сторінка {self.current_page + 1}/{self.total_pages}**\n"
                           f"**Обрано ролей:** {len(self.selected_roles)}\n" + 
                           (", ".join([role.mention for role in self.selected_roles[:10]]) + 
                            (f" і ще {len(self.selected_roles) - 10}..." if len(self.selected_roles) > 10 else "") 
                            if self.selected_roles else "Жодної ролі не обрано")
            )
            
            await interaction.response.edit_message(embed=embed, view=self)

    async def select_all_on_page(self, interaction: discord.Interaction):
        page_roles = self.get_page_roles()
        for role in page_roles:
            if role not in self.selected_roles:
                self.selected_roles.append(role)
        
        self.update_select()
        
        embed = discord.Embed(
            title="🏆 Крок 1: Вибір ролей",
            color=0x7c7cf0,
            description=f"**Сторінка {self.current_page + 1}/{self.total_pages}**\n"
                       f"**Обрано ролей:** {len(self.selected_roles)}\n" + 
                       (", ".join([role.mention for role in self.selected_roles[:10]]) + 
                        (f" і ще {len(self.selected_roles) - 10}..." if len(self.selected_roles) > 10 else "") 
                        if self.selected_roles else "Жодної ролі не обрано")
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def clear_all(self, interaction: discord.Interaction):
        self.selected_roles.clear()
        self.update_select()
        
        embed = discord.Embed(
            title="🏆 Крок 1: Вибір ролей",
            color=0x7c7cf0,
            description=f"**Сторінка {self.current_page + 1}/{self.total_pages}**\n"
                       f"**Обрано ролей:** 0\nЖодної ролі не обрано"
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def continue_setup(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = ActivityTypeView(self.selected_roles)
        
        embed = discord.Embed(
            title="🏆 Крок 2: Тип активності",
            color=0x7c7cf0,
            description=f"Обрано ролей: {', '.join([role.mention for role in self.selected_roles[:5]])}" +
                       (f" і ще {len(self.selected_roles) - 5}..." if len(self.selected_roles) > 5 else "") +
                       "\n\nОбери тип активності для цих ролей:"
        )
        
        await interaction.edit_original_response(embed=embed, view=view)

class RoleSelect(discord.ui.Select):
    def __init__(self, roles: List[discord.Role], selected: List[discord.Role]):
        self.available_roles = roles
        self.selected_roles = selected
        
        options = []
        for role in roles:
            is_selected = role in selected
            options.append(discord.SelectOption(
                label=role.name[:100],
                value=str(role.id),
                description=f"Позиція: {role.position}" + (" • ✅ Обрано" if is_selected else ""),
                emoji="✅" if is_selected else "⚪"
            ))
        
        super().__init__(
            placeholder="Обери ролі для налаштування...",
            options=options,
            max_values=min(len(options), 25)
        )

    async def callback(self, interaction: discord.Interaction):
        # Оновлюємо список обраних ролей
        new_selected = []
        for role_id in self.values:
            role = interaction.guild.get_role(int(role_id))
            if role:
                new_selected.append(role)
        
        # Видаляємо з обраних ті, що не в поточному виборі
        current_page_roles = self.view.get_page_roles()
        self.view.selected_roles = [role for role in self.view.selected_roles if role not in current_page_roles]
        # Додаємо нові обрані
        self.view.selected_roles.extend(new_selected)
        
        self.view.update_select()
        
        embed = discord.Embed(
            title="🏆 Крок 1: Вибір ролей",
            color=0x7c7cf0,
            description=f"**Сторінка {self.view.current_page + 1}/{self.view.total_pages}**\n"
                       f"**Обрано ролей:** {len(self.view.selected_roles)}\n" + 
                       (", ".join([role.mention for role in self.view.selected_roles[:10]]) + 
                        (f" і ще {len(self.view.selected_roles) - 10}..." if len(self.view.selected_roles) > 10 else "") 
                        if self.view.selected_roles else "Жодної ролі не обрано")
        )
        
        await interaction.response.edit_message(embed=embed, view=self.view)

class ConfigDeleteView(discord.ui.View):
    def __init__(self, guild_id: str, configs: List[dict]):
        super().__init__(timeout=300)
        self.guild_id = guild_id
        self.configs = configs
        self.setup_select()

    def setup_select(self):
        if not self.configs:
            return
        
        activity_names = {
            ActivityType.CHAT: "📝 Чат",
            ActivityType.VOICE: "🎤 Войс",
            ActivityType.COMBINED: "🏆 Загальна"
        }
        
        # Групуємо конфігурації по ролях для зручності
        role_configs = {}
        for config in self.configs:
            role_id = config["role_id"]
            if role_id not in role_configs:
                role_configs[role_id] = []
            role_configs[role_id].append(config)
        
        options = []
        for role_id, configs_list in list(role_configs.items())[:25]:  # Discord limit
            guild = discord.utils.get(discord.Client().guilds, id=int(self.guild_id)) if hasattr(discord.Client(), 'guilds') else None
            role_name = f"Роль ID: {role_id}"  # Fallback
            
            # Створюємо опис конфігурацій для цієї ролі
            config_descriptions = []
            for config in configs_list:
                activity = activity_names.get(config["activity_type"], config["activity_type"])
                position = config["top_position"]
                duration = config["duration_days"]
                config_descriptions.append(f"{activity} • Топ {position} • {duration}д")
            
            options.append(discord.SelectOption(
                label=role_name[:100],
                value=role_id,
                description=(" | ".join(config_descriptions))[:100],
                emoji="🗑️"
            ))
        
        if options:
            select = discord.ui.Select(
                placeholder="Обери ролі для видалення конфігурацій...",
                options=options,
                max_values=min(len(options), 25)
            )
            select.callback = self.delete_configs
            self.add_item(select)

    async def delete_configs(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        try:
            deleted_count = 0
            for role_id in interaction.data['values']:
                result = await db.weekly_roles.delete_many({
                    "guild_id": self.guild_id,
                    "role_id": role_id
                })
                deleted_count += result.deleted_count
            
            embed = discord.Embed(
                title="✅ Конфігурації видалено",
                color=0x00ff00,
                description=f"Успішно видалено **{deleted_count}** конфігурацій для **{len(interaction.data['values'])}** ролей."
            )
            
            embed.add_field(
                name="📋 Видалені ролі",
                value="\n".join([f"• Роль ID: {role_id}" for role_id in interaction.data['values']]),
                inline=False
            )
            
            embed.set_footer(text=f"Видалив: {interaction.user.display_name}")
            
            await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Помилка",
                color=0xff0000,
                description=f"Не вдалося видалити конфігурації: {str(e)}"
            )
            await interaction.edit_original_response(embed=embed, view=None)

# Решта коду залишається без змін...
class ActivityTypeView(discord.ui.View):
    def __init__(self, roles: List[discord.Role]):
        super().__init__(timeout=300)
        self.roles = roles
        self.activity_type = None

    @discord.ui.button(label="Топ чату", emoji="📝", style=discord.ButtonStyle.primary, row=0)
    async def chat_top(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.activity_type = ActivityType.CHAT
        await self.continue_to_positions(interaction)

    @discord.ui.button(label="Топ войсу", emoji="🎤", style=discord.ButtonStyle.primary, row=0)
    async def voice_top(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.activity_type = ActivityType.VOICE
        await self.continue_to_positions(interaction)

    @discord.ui.button(label="Загальний топ", emoji="🏆", style=discord.ButtonStyle.primary, row=0)
    async def combined_top(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.activity_type = ActivityType.COMBINED
        await self.continue_to_positions(interaction)

    async def continue_to_positions(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = PositionSelectView(self.roles, self.activity_type)
        
        activity_names = {
            ActivityType.CHAT: "📝 Активність в чаті",
            ActivityType.VOICE: "🎤 Активність у войсі", 
            ActivityType.COMBINED: "🏆 Загальна активність"
        }
        
        embed = discord.Embed(
            title="🏆 Крок 3: Топ позиції",
            color=0x7c7cf0,
            description=f"**Ролі:** {', '.join([role.mention for role in self.roles[:5]])}" +
                       (f" і ще {len(self.roles) - 5}..." if len(self.roles) > 5 else "") + "\n" +
                       f"**Тип:** {activity_names[self.activity_type]}\n\n" +
                       f"Обери які топ позиції будуть отримувати ці ролі:"
        )
        
        await interaction.edit_original_response(embed=embed, view=view)

class PositionSelectView(discord.ui.View):
    def __init__(self, roles: List[discord.Role], activity_type: str):
        super().__init__(timeout=300)
        self.roles = roles
        self.activity_type = activity_type
        self.top_positions = []

    @discord.ui.select(
        placeholder="Обери топ позиції (можна декілька)...",
        options=[
            discord.SelectOption(label="Топ 1", value="1", emoji="🥇"),
            discord.SelectOption(label="Топ 2", value="2", emoji="🥈"), 
            discord.SelectOption(label="Топ 3", value="3", emoji="🥉"),
            discord.SelectOption(label="Топ 4", value="4", emoji="4️⃣"),
            discord.SelectOption(label="Топ 5", value="5", emoji="5️⃣"),
            discord.SelectOption(label="Топ 1-5", value="1-5", emoji="🏆"),
            discord.SelectOption(label="Топ 1-10", value="1-10", emoji="🔝"),
            discord.SelectOption(label="Топ 1-15", value="1-15", emoji="⭐"),
        ],
        max_values=8
    )
    async def position_select(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.top_positions = select.values
        
        # Кнопка продовження
        if not hasattr(self, 'continue_btn'):
            self.continue_btn = discord.ui.Button(
                label="Продовжити",
                style=discord.ButtonStyle.green,
                emoji="✅",
                row=1
            )
            self.continue_btn.callback = self.continue_to_duration
            self.add_item(self.continue_btn)
        
        positions_text = ", ".join([f"Топ {pos}" for pos in self.top_positions])
        
        embed = discord.Embed(
            title="🏆 Крок 3: Топ позиції",
            color=0x7c7cf0,
            description=f"**Ролі:** {', '.join([role.mention for role in self.roles[:5]])}" +
                       (f" і ще {len(self.roles) - 5}..." if len(self.roles) > 5 else "") + "\n" +
                       f"**Тип:** {self.activity_type}\n"
                       f"**Позиції:** {positions_text}\n\n"
                       f"✅ Натисни 'Продовжити' для переходу до наступного кроку"
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def continue_to_duration(self, interaction: discord.Interaction):
        await interaction.response.defer()
        view = DurationSelectView(self.roles, self.activity_type, self.top_positions)
        
        embed = discord.Embed(
            title="🏆 Крок 4: Тривалість",
            color=0x7c7cf0,
            description=f"Обери як часто система має оновлювати ці ролі:"
        )
        
        await interaction.edit_original_response(embed=embed, view=view)

class DurationSelectView(discord.ui.View):
    def __init__(self, roles: List[discord.Role], activity_type: str, top_positions: List[str]):
        super().__init__(timeout=300)
        self.roles = roles
        self.activity_type = activity_type
        self.top_positions = top_positions

    @discord.ui.button(label="7 днів", emoji="1️⃣", style=discord.ButtonStyle.secondary, row=0)
    async def seven_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.continue_to_logs(interaction, 7)

    @discord.ui.button(label="14 днів", emoji="2️⃣", style=discord.ButtonStyle.secondary, row=0) 
    async def fourteen_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.continue_to_logs(interaction, 14)

    @discord.ui.button(label="30 днів", emoji="3️⃣", style=discord.ButtonStyle.secondary, row=0)
    async def thirty_days(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.continue_to_logs(interaction, 30)

    async def continue_to_logs(self, interaction: discord.Interaction, duration: int):
        await interaction.response.defer()
        view = LogChannelSelectView(self.roles, self.activity_type, self.top_positions, duration)
        
        embed = discord.Embed(
            title="🏆 Крок 5: Канал логів (опціонально)",
            color=0x7c7cf0,
            description=f"Обери канал для логування змін ролей або пропусти цей крок:"
        )
        
        await interaction.edit_original_response(embed=embed, view=view)

class LogChannelSelectView(discord.ui.View):
    def __init__(self, roles: List[discord.Role], activity_type: str, top_positions: List[str], duration: int):
        super().__init__(timeout=300)
        self.roles = roles
        self.activity_type = activity_type
        self.top_positions = top_positions
        self.duration = duration
        self.log_channel = None
        self.setup_select()

    def setup_select(self):
        text_channels = [ch for ch in self.roles[0].guild.text_channels if ch.permissions_for(self.roles[0].guild.me).send_messages][:25]
        
        if text_channels:
            options = []
            for channel in text_channels:
                options.append(discord.SelectOption(
                    label=f"#{channel.name}"[:100],
                    value=str(channel.id),
                    description=channel.category.name if channel.category else "Без категорії"
                ))
            
            select = discord.ui.Select(
                placeholder="Обери канал для логів...",
                options=options,
                row=0
            )
            select.callback = self.channel_selected
            self.add_item(select)

        # Кнопки
        skip_btn = discord.ui.Button(label="Пропустити", style=discord.ButtonStyle.secondary, emoji="⏭️", row=1)
        skip_btn.callback = lambda i: self.finish_setup(i, None)
        self.add_item(skip_btn)

    async def channel_selected(self, interaction: discord.Interaction):
        channel_id = int(interaction.data['values'][0])
        self.log_channel = interaction.guild.get_channel(channel_id)
        
        # Додаємо кнопку завершення
        finish_btn = discord.ui.Button(
            label=f"Завершити з #{self.log_channel.name}",
            style=discord.ButtonStyle.green,
            emoji="✅",
            row=2
        )
        finish_btn.callback = lambda i: self.finish_setup(i, self.log_channel)
        self.add_item(finish_btn)
        
        embed = discord.Embed(
            title="🏆 Крок 5: Канал логів",
            color=0x7c7cf0,
            description=f"**Обрано канал:** {self.log_channel.mention}\n\n✅ Натисни 'Завершити' щоб зберегти налаштування"
        )
        
        await interaction.response.edit_message(embed=embed, view=self)

    async def finish_setup(self, interaction: discord.Interaction, log_channel: Optional[discord.TextChannel]):
        await interaction.response.defer()
        
        try:
            # Зберігаємо конфігурацію в БД
            for role in self.roles:
                for position in self.top_positions:
                    config_data = {
                        "guild_id": str(interaction.guild.id),
                        "role_id": str(role.id),
                        "activity_type": self.activity_type,
                        "top_position": position,
                        "duration_days": self.duration,
                        "log_channel_id": str(log_channel.id) if log_channel else None,
                        "enabled": True,
                        "created_by": interaction.user.id,
                        "created_at": datetime.utcnow(),
                        "next_update": datetime.utcnow() + timedelta(days=self.duration)
                    }
                    
                    await db.weekly_roles.update_one(
                        {
                            "guild_id": str(interaction.guild.id),
                            "role_id": str(role.id),
                            "top_position": position
                        },
                        {"$set": config_data},
                        upsert=True
                    )

            # Підсумок
            activity_names = {
                ActivityType.CHAT: "📝 Чат",
                ActivityType.VOICE: "🎤 Войс",
                ActivityType.COMBINED: "🏆 Загальна"
            }
            
            positions_text = ", ".join([f"Топ {pos}" for pos in self.top_positions])
            roles_text = ", ".join([role.mention for role in self.roles[:5]])
            if len(self.roles) > 5:
                roles_text += f" і ще {len(self.roles) - 5}..."
            
            embed = discord.Embed(
                title="✅ Налаштування завершено!",
                color=0x00ff00,
                description="Система щотижневих ролей успішно налаштована"
            )
            
            embed.add_field(
                name="📋 Конфігурація",
                value=f"**Ролі:** {roles_text}\n"
                     f"**Активність:** {activity_names[self.activity_type]}\n" 
                     f"**Позиції:** {positions_text}\n"
                     f"**Оновлення:** Кожні {self.duration} днів\n"
                     f"**Логи:** {log_channel.mention if log_channel else 'Вимкнено'}",
                inline=False
            )
            
            next_update = datetime.utcnow() + timedelta(days=self.duration)
            embed.add_field(
                name="⏰ Наступне оновлення",
                value=f"<t:{int(next_update.timestamp())}:F>",
                inline=False
            )
            
            embed.set_footer(text=f"Налаштував: {interaction.user.display_name}")
            
            await interaction.edit_original_response(embed=embed, view=None)
            
        except Exception as e:
            embed = discord.Embed(
                title="❌ Помилка",
                color=0xff0000,
                description=f"Не вдалося зберегти налаштування: {str(e)}"
            )
            await interaction.edit_original_response(embed=embed, view=None)

class WeeklyRoleSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.role_updater.start()

    def cog_unload(self):
        self.role_updater.cancel()

    @app_commands.command(name="weekly-role", description="[АДМІН] Налаштування системи щотижневих ролей")
    async def weekly_role(self, interaction: discord.Interaction):
        """Налаштування системи щотижневих ролей"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ У тебе немає прав для управління ролями!", ephemeral=True)
            return

        embed = discord.Embed(
            title="🏆 Крок 1: Вибір ролей",
            color=0x7c7cf0,
            description="Обери ролі, які мають видаватися за активність.\nМожна обрати декілька ролей для однакових налаштувань.\n\n" +
                       "💡 Використовуй кнопки навігації для перегляду всіх ролей на сервері."
        )

        view = RoleSelectView(interaction.guild)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @tasks.loop(hours=1)  # Перевіряємо кожну годину
    async def role_updater(self):
        """Оновлює ролі згідно з розкладом"""
        if db is None:
            return

        current_time = datetime.utcnow()
        
        # Знаходимо всі конфігурації, які потрібно оновити
        configs_to_update = await db.weekly_roles.find({
            "enabled": True,
            "next_update": {"$lte": current_time}
        }).to_list(1000)

        for config in configs_to_update:
            try:
                guild = self.bot.get_guild(int(config["guild_id"]))
                if not guild:
                    continue
                
                await self._process_role_config(guild, config)
                
                # Оновлюємо час наступного оновлення
                next_update = current_time + timedelta(days=config["duration_days"])
                await db.weekly_roles.update_one(
                    {"_id": config["_id"]},
                    {"$set": {"next_update": next_update}}
                )
                
            except Exception as e:
                print(f"Error processing role config {config.get('_id')}: {e}")

    async def _process_role_config(self, guild: discord.Guild, config: dict):
        """Обробляє одну конфігурацію ролі"""
        role = guild.get_role(int(config["role_id"]))
        if not role or role.position >= guild.me.top_role.position:
            return

        # Отримуємо топ користувачів
        top_users = await self._get_top_users_for_config(guild, config)
        
        # Оновлюємо ролі
        assigned, removed = await self._update_role_for_users(guild, role, top_users)
        
        # Логування
        if config.get("log_channel_id") and (assigned or removed):
            await self._log_role_changes(guild, config, role, assigned, removed)

    async def _get_top_users_for_config(self, guild: discord.Guild, config: dict) -> List[int]:
        """Отримує список користувачів для конфігурації"""
        activity_type = config["activity_type"]
        position = config["top_position"]
        duration = config["duration_days"]
        
        # Визначаємо кількість користувачів
        if "-" in position:
            # Діапазон (наприклад "1-5")
            start, end = map(int, position.split("-"))
            count = end
        else:
            # Конкретна позиція (наприклад "3")
            count = int(position)

        # Отримуємо дані активності
        end_date = datetime.now()
        start_date = end_date - timedelta(days=duration)
        date_range = [(start_date + timedelta(days=i)).strftime("%Y-%m-%d") for i in range(duration)]

        # Отримуємо користувачів сервера
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
            
            if activity_type == ActivityType.CHAT:
                # Підраховуємо повідомлення (10 XP за повідомлення)
                activity_score = 0
                for date_str in date_range:
                    daily_xp = history.get(date_str, 0)
                    activity_score += daily_xp // 10
                    
            elif activity_type == ActivityType.VOICE:
                # Підраховуємо час в войсі (5 XP за хвилину)
                activity_score = 0
                for date_str in date_range:
                    daily_xp = history.get(date_str, 0)
                    activity_score += daily_xp // 5
                    
            elif activity_type == ActivityType.COMBINED:
                # Загальний XP
                activity_score = 0
                for date_str in date_range:
                    activity_score += history.get(date_str, 0)
            
            if activity_score > 0:
                user_activity.append((user_id, activity_score))

        # Сортуємо та беремо топ
        user_activity.sort(key=lambda x: x[1], reverse=True)
        
        if "-" in position:
            # Діапазон позицій
            start, end = map(int, position.split("-"))
            selected_users = [user_id for user_id, _ in user_activity[start-1:end]]
        else:
            # Конкретна позиція
            pos = int(position)
            if pos <= len(user_activity):
                selected_users = [user_activity[pos-1][0]]
            else:
                selected_users = []

        return selected_users

    async def _update_role_for_users(self, guild: discord.Guild, role: discord.Role, target_users: List[int]) -> tuple:
        """Оновлює ролі для користувачів"""
        assigned = []
        removed = []

        # Поточні власники ролі
        current_holders = [member.id for member in guild.members if role in member.roles]

        # Знімаємо роль у тих, хто не повинен її мати
        for user_id in current_holders:
            if user_id not in target_users:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.remove_roles(role, reason="Система щотижневих ролей - не в топі")
                        removed.append(member)
                    except:
                        pass

        # Видаємо роль тим, хто повинен її мати
        for user_id in target_users:
            if user_id not in current_holders:
                member = guild.get_member(user_id)
                if member:
                    try:
                        await member.add_roles(role, reason="Система щотижневих ролей - в топі")
                        assigned.append(member)
                    except:
                        pass

        return assigned, removed

    async def _log_role_changes(self, guild: discord.Guild, config: dict, role: discord.Role, assigned: List[discord.Member], removed: List[discord.Member]):
        """Логує зміни ролей"""
        log_channel = guild.get_channel(int(config["log_channel_id"]))
        if not log_channel:
            return

        embed = discord.Embed(
            title="🏆 Оновлення щотижневих ролей",
            color=0x7c7cf0,
            timestamp=datetime.utcnow()
        )

        activity_names = {
            ActivityType.CHAT: "📝 Чат",
            ActivityType.VOICE: "🎤 Войс", 
            ActivityType.COMBINED: "🏆 Загальна"
        }

        embed.add_field(
            name="📋 Інформація",
            value=f"**Роль:** {role.mention}\n"
                 f"**Активність:** {activity_names[config['activity_type']]}\n"
                 f"**Позиція:** Топ {config['top_position']}",
            inline=False
        )

        if assigned:
            assigned_text = "\n".join([f"• {member.mention}" for member in assigned[:10]])
            if len(assigned) > 10:
                assigned_text += f"\n... і ще {len(assigned) - 10}"
            embed.add_field(name="✅ Видано роль", value=assigned_text, inline=True)

        if removed:
            removed_text = "\n".join([f"• {member.mention}" for member in removed[:10]])
            if len(removed) > 10:
                removed_text += f"\n... і ще {len(removed) - 10}"
            embed.add_field(name="❌ Знято роль", value=removed_text, inline=True)

        embed.set_footer(text="Система щотижневих ролей")

        try:
            await log_channel.send(embed=embed)
        except:
            pass

    @role_updater.before_loop
    async def before_role_updater(self):
        await self.bot.wait_until_ready()

    @app_commands.command(name="weekly-status", description="[АДМІН] Переглянути статус системи щотижневих ролей")
    async def weekly_status(self, interaction: discord.Interaction):
        """Показує статус системи щотижневих ролей"""
        if not interaction.user.guild_permissions.manage_roles:
            await interaction.response.send_message("❌ У тебе немає прав для управління ролями!", ephemeral=True)
            return

        await interaction.response.defer(ephemeral=True)

        try:
            configs = await db.weekly_roles.find({
                "guild_id": str(interaction.guild.id),
                "enabled": True
            }).to_list(100)

            if not configs:
                embed = discord.Embed(
                    title="📊 Статус системи щотижневих ролей",
                    color=0x7c7cf0,
                    description="❌ Система не налаштована\n\nВикористай `/weekly-role` для налаштування"
                )
                await interaction.followup.send(embed=embed)
                return

            embed = discord.Embed(
                title="📊 Статус системи щотижневих ролей",
                color=0x7c7cf0,
                description=f"Знайдено **{len(configs)}** активних конфігурацій"
            )

            activity_names = {
                ActivityType.CHAT: "📝 Чат",
                ActivityType.VOICE: "🎤 Войс",
                ActivityType.COMBINED: "🏆 Загальна"
            }

            # Групуємо по ролях
            role_configs = {}
            for config in configs:
                role_id = config["role_id"]
                if role_id not in role_configs:
                    role_configs[role_id] = []
                role_configs[role_id].append(config)

            for role_id, role_configs_list in list(role_configs.items())[:10]:  # Максимум 10 ролей
                role = interaction.guild.get_role(int(role_id))
                role_name = role.name if role else f"Видалена роль (ID: {role_id})"

                config_texts = []
                for config in role_configs_list:
                    activity_type = activity_names.get(config["activity_type"], config["activity_type"])
                    position = config["top_position"]
                    duration = config["duration_days"]
                    next_update = config.get("next_update", datetime.utcnow())
                    
                    config_text = f"{activity_type} • Топ {position} • {duration}д • <t:{int(next_update.timestamp())}:R>"
                    config_texts.append(config_text)

                embed.add_field(
                    name=f"{role_name}",
                    value="\n".join(config_texts),
                    inline=False
                )

            # Додаємо кнопку видалення конфігурацій
            delete_view = discord.ui.View(timeout=300)
            delete_btn = discord.ui.Button(
                label="🗑️ Видалити конфігурації",
                style=discord.ButtonStyle.danger,
                emoji="🗑️"
            )
            
            async def delete_callback(button_interaction):
                await button_interaction.response.defer()
                
                # Створюємо view для видалення
                delete_config_view = ConfigDeleteView(str(interaction.guild.id), configs)
                
                delete_embed = discord.Embed(
                    title="🗑️ Видалення конфігурацій",
                    color=0xff6b6b,
                    description="Обери ролі, для яких потрібно видалити всі конфігурації щотижневих ролей.\n"
                               "**⚠️ Увага:** Ця дія незворотна!"
                )
                
                await button_interaction.edit_original_response(embed=delete_embed, view=delete_config_view)
            
            delete_btn.callback = delete_callback
            delete_view.add_item(delete_btn)

            await interaction.followup.send(embed=embed, view=delete_view)

        except Exception as e:
            await interaction.followup.send(f"❌ Помилка: {str(e)}")

async def setup(bot):
    await bot.add_cog(WeeklyRoleSystem(bot))