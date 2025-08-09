import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime, timedelta
import asyncio
import json
from typing import Optional
from modules.db import get_database

db = get_database()

# Типи тікетів
TICKET_TYPES = {
    "role_application": {
        "name": "Заявка на роль",
        "description": "Подати заявку на отримання ролі",
        "questions": [
            "Чому ви хочете отримати цю роль?",
            "Чи маєте ви досвід, пов'язаний з цією роллю?",
            "Як ви плануєте використовувати цю роль?",
            "Додаткова інформація про себе:"
        ]
    },
    "server_suggestion": {
        "name": "Пропозиція для сервера",
        "description": "Поділитися ідеями для покращення сервера",
        "questions": [
            "Яка ваша пропозиція?",
            "Як це покращить сервер?",
            "Чи розглядали ви можливі недоліки?",
            "Додаткові деталі або коментарі:"
        ]
    },
    "bug_report": {
        "name": "Звіт про баг",
        "description": "Повідомити про технічні проблеми",
        "questions": [
            "Опишіть проблему детально:",
            "Як відтворити цю помилку?",
            "Що ви очікували побачити?",
            "Додаткова інформація (скріншоти, логи):"
        ]
    },
    "general_support": {
        "name": "Загальна підтримка",
        "description": "Питання або допомога від модерації",
        "questions": [
            "Опишіть ваше питання або проблему:",
            "Чи намагались ви вирішити це самостійно?",
            "Додаткові деталі:"
        ]
    },
    "complaint": {
        "name": "Скарга",
        "description": "Подати скаргу на користувача або ситуацію",
        "questions": [
            "На кого або що ви скаржитесь?",
            "Що сталося? Опишіть ситуацію:",
            "Чи є у вас докази (скріншоти, повідомлення)?",
            "Додаткова інформація:"
        ]
    }
}

async def get_guild_config(guild_id: int):
    """Отримує конфігурацію гільдії з бази даних"""
    config = await db.ticket_config.find_one({"guild_id": guild_id})
    if not config:
        # Створюємо конфігурацію за замовчуванням
        default_config = {
            "guild_id": guild_id,
            "moderator_role_id": None,
            "category_id": None,
            "log_channel_id": None,
            "available_roles": []
        }
        await db.ticket_config.insert_one(default_config)
        return default_config
    return config

async def update_guild_config(guild_id: int, updates: dict):
    """Оновлює конфігурацію гільдії"""
    await db.ticket_config.update_one(
        {"guild_id": guild_id},
        {"$set": updates},
        upsert=True
    )

async def save_ticket_stat(guild_id: int):
    """Зберігає статистику створення тікета"""
    today = datetime.now().strftime('%Y-%m-%d')
    await db.ticket_stats.update_one(
        {"guild_id": guild_id, "date": today},
        {"$inc": {"count": 1}},
        upsert=True
    )

async def get_week_stats(guild_id: int):
    """Отримує статистику за 7 днів"""
    stats = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d')
        stat = await db.ticket_stats.find_one({"guild_id": guild_id, "date": date})
        count = stat["count"] if stat else 0
        stats.append((date, count))
    return stats

class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for ticket_type, config in TICKET_TYPES.items():
            options.append(
                discord.SelectOption(
                    label=config["name"],
                    description=config["description"], 
                    value=ticket_type
                )
            )
        
        super().__init__(
            placeholder="Оберіть тип тікета...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="ticket_type_select_main"
        )
    
    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        guild_config = await get_guild_config(interaction.guild.id)
        
        if ticket_type == "role_application":
            # Якщо це заявка на роль - показуємо вибір ролей
            if not guild_config["available_roles"]:
                await interaction.response.send_message(
                    "Адміністратори ще не налаштували доступні ролі для заявок.", 
                    ephemeral=True
                )
                return
            
            # Отримуємо доступні ролі
            available_roles = []
            for role_id in guild_config["available_roles"]:
                role = interaction.guild.get_role(role_id)
                if role and not role.is_bot_managed():
                    available_roles.append(role)
            
            if not available_roles:
                await interaction.response.send_message(
                    "Всі налаштовані ролі недоступні або видалені.", 
                    ephemeral=True
                )
                return
            
            view = RoleSelectView(interaction.guild, available_roles)
            embed = discord.Embed(
                title="Заявка на роль",
                description="Оберіть роль, на яку хочете подати заявку:",
                color=0x2b2d31
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
        else:
            # Для інших типів - відразу створюємо тікет
            await self.create_ticket(interaction, ticket_type)
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, role_id: int = None):
        config = TICKET_TYPES[ticket_type]
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо чи вже є відкритий тікет
        existing_ticket = None
        for channel in interaction.guild.text_channels:
            if (channel.name.startswith(ticket_type) and 
                str(interaction.user.id) in channel.name):
                existing_ticket = channel
                break
        
        if existing_ticket:
            await interaction.response.send_message(
                f"У вас вже є відкритий тікет: {existing_ticket.mention}",
                ephemeral=True
            )
            return
        
        # Назва тікета
        if role_id:
            role = interaction.guild.get_role(role_id)
            ticket_name = f"role-{role.name if role else 'unknown'}-{interaction.user.id}"
        else:
            ticket_name = f"{ticket_type}-{interaction.user.id}"
        
        # Знаходимо або створюємо категорію
        category = None
        if guild_config["category_id"]:
            category = interaction.guild.get_channel(guild_config["category_id"])
        
        if not category:
            # Шукаємо категорію з назвою "Tickets" або створюємо нову
            for cat in interaction.guild.categories:
                if cat.name.lower() in ["tickets", "тікети", "тикеты"]:
                    category = cat
                    await update_guild_config(interaction.guild.id, {"category_id": cat.id})
                    break
            
            if not category:
                try:
                    category = await interaction.guild.create_category("Тікети")
                    await update_guild_config(interaction.guild.id, {"category_id": category.id})
                except Exception as e:
                    await interaction.response.send_message(
                        f"Не вдалося створити категорію для тікетів: {e}", 
                        ephemeral=True
                    )
                    return
        
        # Права доступу
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, 
                send_messages=True, 
                attach_files=True,
                embed_links=True
            ),
        }
        
        # Додаємо права модераторам
        if guild_config["moderator_role_id"]:
            mod_role = interaction.guild.get_role(guild_config["moderator_role_id"])
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True, 
                    send_messages=True, 
                    manage_messages=True,
                    attach_files=True,
                    embed_links=True
                )
        
        try:
            channel = await category.create_text_channel(
                name=ticket_name.lower().replace(" ", "-")[:50],
                overwrites=overwrites,
                topic=f"Тікет {config['name']} | Користувач: {interaction.user} | ID: {interaction.user.id}"
            )
            
            # Зберігаємо інформацію про тікет в базу
            ticket_data = {
                "guild_id": interaction.guild.id,
                "channel_id": channel.id,
                "user_id": interaction.user.id,
                "ticket_type": ticket_type,
                "role_id": role_id,
                "created_at": datetime.now(),
                "status": "open"
            }
            await db.tickets.insert_one(ticket_data)
            
            # Embed з інформацією
            embed = discord.Embed(
                title=f"{config['name']}",
                description=f"**Користувач:** {interaction.user.mention}\n**Створено:** <t:{int(datetime.now().timestamp())}:F>",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            
            if role_id:
                role = interaction.guild.get_role(role_id)
                embed.add_field(
                    name="Запитувана роль",
                    value=f"{role.mention if role else 'Невідома роль'}",
                    inline=True
                )
            
            embed.add_field(
                name="Інструкції",
                value="• Відповідайте на запитання чесно та детально\n• Очікуйте відповіді від модерації\n• Не спамте в каналі",
                inline=False
            )
            
            embed.set_footer(text=f"ID користувача: {interaction.user.id}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Створюємо view з кнопками для модерації
            if ticket_type == "role_application":
                view = RoleApplicationButtons(role_id, interaction.user.id, channel.id)
            else:
                view = GeneralTicketButtons(ticket_type, interaction.user.id, channel.id)
            
            # Відправляємо повідомлення
            mod_role = interaction.guild.get_role(guild_config["moderator_role_id"]) if guild_config["moderator_role_id"] else None
            message = await channel.send(
                f"{interaction.user.mention} | {mod_role.mention if mod_role else '@Модерація'}",
                embed=embed,
                view=view
            )
            
            # Закріплюємо повідомлення
            try:
                await message.pin()
            except:
                pass
            
            # Починаємо задавати питання
            await self.ask_questions(channel, config['questions'], interaction.user)
            
            # Зберігаємо статистику
            await save_ticket_stat(interaction.guild.id)
            
            # Відповідь користувачу
            success_embed = discord.Embed(
                title="Тікет успішно створено",
                description=f"**Ваш тікет:** {channel.mention}\n\n" +
                           f"Тип: {config['name']}\n" +
                           f"Очікуйте відповіді від модерації\n" +
                           f"Не закривайте цю вкладку до завершення",
                color=0x57f287
            )
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=success_embed, view=None)
            else:
                await interaction.response.send_message(embed=success_embed, view=None, ephemeral=True)
            
            # Лог у канал логів
            await self.log_ticket_creation(interaction.guild, interaction.user, config, channel, guild_config)
            
        except Exception as e:
            error_message = f"Помилка створення тікета: {e}"
            if interaction.response.is_done():
                await interaction.edit_original_response(content=error_message, embed=None, view=None)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
    
    async def ask_questions(self, channel: discord.TextChannel, questions: list, user: discord.Member):
        """Задає питання користувачу"""
        await asyncio.sleep(3)  # Невелика затримка
        
        questions_embed = discord.Embed(
            title="Анкета",
            description="Будь ласка, дайте відповіді на наступні питання:",
            color=0x2b2d31
        )
        
        for i, question in enumerate(questions, 1):
            questions_embed.add_field(
                name=f"Питання {i}",
                value=question,
                inline=False
            )
        
        questions_embed.set_footer(text="Відповідайте по одному питанню в повідомленні")
        await channel.send(embed=questions_embed)
    
    async def log_ticket_creation(self, guild: discord.Guild, user: discord.Member, config: dict, channel: discord.TextChannel, guild_config: dict):
        """Логування створення тікета"""
        if not guild_config["log_channel_id"]:
            return
        
        log_channel = guild.get_channel(guild_config["log_channel_id"])
        if not log_channel:
            return
        
        try:
            embed = discord.Embed(
                title="Новий тікет створено",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            embed.add_field(name="Користувач", value=f"{user.mention} (`{user.id}`)", inline=True)
            embed.add_field(name="Тип", value=config['name'], inline=True)
            embed.add_field(name="Канал", value=channel.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await log_channel.send(embed=embed)
        except:
            pass

class RoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        options = []
        
        async def get_available_roles():
            guild_config = await get_guild_config(guild.id)
            available_roles = []
            for role_id in guild_config["available_roles"]:
                role = guild.get_role(role_id)
                if role and not role.is_bot_managed():
                    available_roles.append(role)
            return available_roles
        
        # Тут потрібно буде викликати асинхронну функцію в callback
        super().__init__(
            placeholder="Оберіть роль...",
            options=[discord.SelectOption(label="Завантаження...", value="loading")],
            min_values=1,
            max_values=1,
            custom_id="role_select_application"
        )
    
    async def callback(self, interaction: discord.Interaction):
        # Отримуємо актуальні ролі
        guild_config = await get_guild_config(interaction.guild.id)
        
        if interaction.data["values"][0] == "loading":
            # Оновлюємо опції
            available_roles = []
            for role_id in guild_config["available_roles"]:
                role = interaction.guild.get_role(role_id)
                if role and not role.is_bot_managed():
                    available_roles.append(role)
            
            if not available_roles:
                await interaction.response.send_message("Немає доступних ролей для заявки!", ephemeral=True)
                return
            
            # Створюємо новий view з правильними опціями
            view = RoleSelectView(interaction.guild, available_roles)
            embed = discord.Embed(
                title="Заявка на роль",
                description="Оберіть роль, на яку хочете подати заявку:",
                color=0x2b2d31
            )
            await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            try:
                dm_embed = discord.Embed(
                    title="Тікет вирішено",
                    description=f"Ваш тікет типу **{config['name']}** було вирішено.\n\n" +
                               f"Сервер: **{interaction.guild.name}**\n" +
                               f"Модератор: {interaction.user.mention}\n" +
                               f"Дякуємо за звернення!",
                    color=0x57f287
                )
                await user.send(embed=dm_embed)
            except:
                pass

class RejectModal(discord.ui.Modal, title="Причина відхилення"):
    def __init__(self, role_id: int, user_id: int, channel_id: int):
        super().__init__(timeout=300)
        self.role_id = role_id
        self.user_id = user_id
        self.channel_id = channel_id
    
    reason = discord.ui.TextInput(
        label="Причина відхилення заявки",
        placeholder="Вкажіть чому заявку було відхилено...",
        required=True,
        max_length=1000,
        style=discord.TextStyle.paragraph
    )
    
    async def on_submit(self, interaction: discord.Interaction):
        user = interaction.guild.get_member(self.user_id)
        role = interaction.guild.get_role(self.role_id)
        
        # Оновлюємо статус тікета в базі
        await db.tickets.update_one(
            {"channel_id": self.channel_id},
            {"$set": {
                "status": "rejected", 
                "rejected_by": interaction.user.id, 
                "rejected_at": datetime.now(),
                "reject_reason": self.reason.value
            }}
        )
        
        embed = discord.Embed(
            title="Заявку відхилено",
            description=f"**Користувач:** {user.mention if user else 'Користувач покинув сервер'}\n" +
                       f"**Роль:** {role.mention if role else 'Роль видалена'}\n" +
                       f"**Модератор:** {interaction.user.mention}",
            color=0xed4245,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="Причина відхилення",
            value=self.reason.value,
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            try:
                dm_embed = discord.Embed(
                    title="Заявку відхилено",
                    description=f"На жаль, вашу заявку на роль **{role.name if role else 'невідома роль'}** відхилено.\n\n" +
                               f"Сервер: **{interaction.guild.name}**\n" +
                               f"Причина: {self.reason.value}\n" +
                               f"Ви можете подати нову заявку пізніше",
                    color=0xed4245
                )
                await user.send(embed=dm_embed)
            except:
                pass

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Закрити тікет", style=discord.ButtonStyle.secondary, custom_id="close_ticket_final")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо права
        if not guild_config["moderator_role_id"] or not any(role.id == guild_config["moderator_role_id"] for role in interaction.user.roles):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        # Оновлюємо статус тікета в базі
        await db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {"$set": {"status": "closed", "closed_by": interaction.user.id, "closed_at": datetime.now()}}
        )
        
        embed = discord.Embed(
            title="Тікет закривається",
            description=f"Тікет закрито модератором {interaction.user.mention}\n\n" +
                       f"Час закриття: <t:{int(datetime.now().timestamp())}:F>\n" +
                       f"Канал буде видалено через 15 секунд...",
            color=0xfee75c,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Дякуємо за використання системи тікетів")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Логування закриття
        await self.log_ticket_closure(interaction, guild_config)
        
        # Видаляємо канал через 15 секунд
        await asyncio.sleep(15)
        try:
            await interaction.channel.delete(reason=f"Тікет закрито модератором {interaction.user}")
        except Exception as e:
            print(f"Помилка видалення каналу: {e}")
    
    async def log_ticket_closure(self, interaction: discord.Interaction, guild_config: dict):
        """Логування закриття тікета"""
        if not guild_config["log_channel_id"]:
            return
        
        log_channel = interaction.guild.get_channel(guild_config["log_channel_id"])
        if not log_channel:
            return
        
        try:
            embed = discord.Embed(
                title="Тікет закрито",
                color=0xfee75c,
                timestamp=datetime.now()
            )
            embed.add_field(name="Канал", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
            embed.add_field(name="Час закриття", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
            
            await log_channel.send(embed=embed)
        except:
            pass

class MultiRoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, mode: str, guild_config: dict):
        self.guild = guild
        self.mode = mode  # "add" або "remove"
        self.guild_config = guild_config
        options = []
        
        if mode == "add":
            # Показуємо ролі які НЕ в списку
            for role in guild.roles:
                if (role != guild.default_role and 
                    not role.is_bot_managed() and 
                    role.id != guild_config["moderator_role_id"] and
                    not role.permissions.administrator and
                    not role.permissions.manage_guild and
                    role.id not in guild_config["available_roles"]):
                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=str(role.id)
                        )
                    )
        else:
            # Показуємо ролі які В списку
            for role_id in guild_config["available_roles"]:
                role = guild.get_role(role_id)
                if role:
                    options.append(
                        discord.SelectOption(
                            label=role.name,
                            value=str(role.id)
                        )
                    )
        
        if not options:
            options.append(
                discord.SelectOption(
                    label="Немає доступних ролей",
                    value="no_roles"
                )
            )
        
        placeholder = "Оберіть ролі для додавання..." if mode == "add" else "Оберіть ролі для видалення..."
        
        super().__init__(
            placeholder=placeholder,
            options=options[:25],  # Discord limit
            min_values=1,
            max_values=min(len(options), 25),
            custom_id=f"multi_role_select_{mode}"
        )
    
    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "no_roles":
            text = "Немає ролей для додавання" if self.mode == "add" else "Немає ролей для видалення"
            await interaction.response.send_message(text, ephemeral=True)
            return
        
        changed_roles = []
        
        for role_id_str in self.values:
            role_id = int(role_id_str)
            role = interaction.guild.get_role(role_id)
            
            if not role:
                continue
            
            if self.mode == "add":
                if role_id not in self.guild_config["available_roles"]:
                    self.guild_config["available_roles"].append(role_id)
                    changed_roles.append(f"+ {role.mention}")
            else:  # remove
                if role_id in self.guild_config["available_roles"]:
                    self.guild_config["available_roles"].remove(role_id)
                    changed_roles.append(f"- {role.mention}")
        
        # Оновлюємо конфігурацію в базі даних
        await update_guild_config(interaction.guild.id, {"available_roles": self.guild_config["available_roles"]})
        
        if changed_roles:
            action = "додано" if self.mode == "add" else "видалено"
            embed = discord.Embed(
                title=f"Ролі {action}",
                description="\n".join(changed_roles),
                color=0x57f287 if self.mode == "add" else 0xed4245
            )
            embed.add_field(
                name="Загальна кількість ролей",
                value=f"{len(self.guild_config['available_roles'])} ролей",
                inline=True
            )
        else:
            embed = discord.Embed(
                title="Нічого не змінено",
                description="Вибрані ролі вже мають відповідний статус",
                color=0xfee75c
            )
        
        await interaction.response.edit_message(embed=embed, view=None)

class MultiRoleView(discord.ui.View):
    def __init__(self, guild: discord.Guild, mode: str):
        super().__init__(timeout=300)
        self.guild = guild
        self.mode = mode
        # Не додаємо селект тут - додамо в interaction_check
    
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        # Отримуємо конфігурацію та додаємо селект
        guild_config = await get_guild_config(self.guild.id)
        
        # Видаляємо старий селект якщо є та додаємо новий
        self.clear_items()
        self.add_item(MultiRoleSelect(self.guild, self.mode, guild_config))
        
        # Оновлюємо повідомлення з новим селектом
        title = "Додавання ролей" if self.mode == "add" else "Видалення ролей"
        description = "Оберіть ролі для додавання до списку заявок:" if self.mode == "add" else "Оберіть ролі для видалення зі списку заявок:"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x2b2d31
        )
        
        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except:
            # Якщо не вдалося редагувати, значить це перший раз
            pass
        
        return True

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        """Викликається при завантаженні cog"""
        # Додаємо persistent views
        self.bot.add_view(TicketMainView())
        self.bot.add_view(RoleApplicationButtons())
        self.bot.add_view(GeneralTicketButtons())
        self.bot.add_view(TicketCloseView())
        print("Persistent views завантажено")
    
    @app_commands.command(name="ticket_setup", description="Налаштування системи тікетів")
    @app_commands.describe(
        action="Дія для виконання",
        channel="Канал для панелі тікетів",
        moderator_role="Роль модераторів",
        log_channel="Канал для логів тікетів",
        category="Категорія для тікетів"
    )
    @app_commands.choices(action=[
        app_commands.Choice(name="Створити панель", value="create_panel"),
        app_commands.Choice(name="Налаштувати конфігурацію", value="configure"),
        app_commands.Choice(name="Показати поточні налаштування", value="show_config")
    ])
    async def ticket_setup(
        self, 
        interaction: discord.Interaction,
        action: str,
        channel: discord.TextChannel = None,
        moderator_role: discord.Role = None,
        log_channel: discord.TextChannel = None,
        category: discord.CategoryChannel = None
    ):
        """Універсальна команда для налаштування системи тікетів"""
        
        # Перевіряємо права
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Тільки адміністратори можуть використовувати цю команду!", ephemeral=True)
            return
        
        guild_config = await get_guild_config(interaction.guild.id)
        
        if action == "create_panel":
            target_channel = channel or interaction.channel
            
            # Головний embed
            main_embed = discord.Embed(
                title="Система тікетів підтримки",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            
            # Додаємо інформацію про типи тікетів
            ticket_info = ""
            for i, (ticket_type, config) in enumerate(TICKET_TYPES.items(), 1):
                ticket_info += f"{i}. {config['name']} | {config['description']}\n"
            
            main_embed.add_field(
                name="Доступні типи тікетів:",
                value=ticket_info.strip(),
                inline=False
            )
            
            main_embed.add_field(
                name="Правила використання:",
                value="• Один активний тікет кожного типу на користувача\n" +
                      "• Відповідайте чесно та детально\n" +
                      "• Будьте ввічливими з модерацією\n" +
                      "• Не створюйте тікети без потреби",
                inline=False
            )
            
            main_embed.set_footer(text="Виберіть опцію з меню нижче")
            
            view = TicketMainView()
            
            # Відправляємо повідомлення
            await target_channel.send(embed=main_embed, view=view)
            
            success_embed = discord.Embed(
                title="Панель тікетів створено",
                description=f"Панель успішно розміщено в {target_channel.mention}\n\n" +
                           f"Користувачі тепер можуть створювати тікети\n" +
                           f"Переконайтесь що ID модераторської ролі вказано правильно",
                color=0x57f287
            )
            
            await interaction.response.send_message(embed=success_embed, ephemeral=True)
        
        elif action == "configure":
            changes_made = []
            updates = {}
            
            if moderator_role:
                updates["moderator_role_id"] = moderator_role.id
                changes_made.append(f"Роль модераторів: {moderator_role.mention}")
            
            if log_channel:
                updates["log_channel_id"] = log_channel.id
                changes_made.append(f"Канал логів: {log_channel.mention}")
            
            if category:
                updates["category_id"] = category.id
                changes_made.append(f"Категорія тікетів: {category.name}")
            
            if updates:
                await update_guild_config(interaction.guild.id, updates)
                embed = discord.Embed(
                    title="Конфігурацію оновлено",
                    description="**Змінено наступні налаштування:**\n\n" + "\n".join(changes_made),
                    color=0x57f287
                )
            else:
                embed = discord.Embed(
                    title="Нічого не змінено",
                    description="Вкажіть параметри для зміни",
                    color=0xfee75c
                )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif action == "show_config":
            # Показуємо поточну конфігурацію
            mod_role = interaction.guild.get_role(guild_config["moderator_role_id"]) if guild_config["moderator_role_id"] else None
            log_ch = interaction.guild.get_channel(guild_config["log_channel_id"]) if guild_config["log_channel_id"] else None
            cat = interaction.guild.get_channel(guild_config["category_id"]) if guild_config["category_id"] else None
            
            embed = discord.Embed(
                title="Поточна конфігурація",
                color=0x2b2d31
            )
            
            embed.add_field(
                name="Роль модераторів",
                value=mod_role.mention if mod_role else "Не налаштовано",
                inline=False
            )
            
            embed.add_field(
                name="Канал логів",
                value=log_ch.mention if log_ch else "Не налаштовано",
                inline=False
            )
            
            embed.add_field(
                name="Категорія тікетів",
                value=cat.name if cat else "Буде створена автоматично",
                inline=False
            )
            
            embed.add_field(
                name="Доступні ролі для заявок",
                value=f"{len(guild_config['available_roles'])} ролей" if guild_config['available_roles'] else "Не налаштовано",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="manage_roles", description="Керування ролями для заявок")
    @app_commands.describe(action="Дія з ролями")
    @app_commands.choices(action=[
        app_commands.Choice(name="Додати ролі", value="add"),
        app_commands.Choice(name="Видалити ролі", value="remove"),
        app_commands.Choice(name="Показати список", value="list")
    ])
    async def manage_roles(self, interaction: discord.Interaction, action: str):
        """Керування ролями для заявок"""
        
        # Перевіряємо права
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Тільки адміністратори можуть використовувати цю команду!", ephemeral=True)
            return
        
        guild_config = await get_guild_config(interaction.guild.id)
        
        if action == "list":
            if not guild_config["available_roles"]:
                embed = discord.Embed(
                    title="Список ролей",
                    description="Немає налаштованих ролей для заявок",
                    color=0xed4245
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(
                title="Доступні ролі для заявок",
                color=0x2b2d31
            )
            
            roles_list = []
            valid_roles = []
            for i, role_id in enumerate(guild_config["available_roles"], 1):
                role = interaction.guild.get_role(role_id)
                if role:
                    roles_list.append(f"{i}. {role.mention}")
                    valid_roles.append(role_id)
                else:
                    roles_list.append(f"{i}. Роль видалена (ID: {role_id})")
            
            # Очищуємо неіснуючі ролі
            if len(valid_roles) != len(guild_config["available_roles"]):
                await update_guild_config(interaction.guild.id, {"available_roles": valid_roles})
            
            embed.add_field(
                name=f"Ролей: {len(valid_roles)}",
                value="\n".join(roles_list) if roles_list else "Немає ролей",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            # Показуємо селект для вибору ролей
            view = MultiRoleView(interaction.guild, action)
            # Додаємо заглушку селекта для початкового відображення
            placeholder_select = discord.ui.Select(
                placeholder="Натисніть тут щоб завантажити ролі...",
                options=[discord.SelectOption(label="Завантаження...", value="loading")],
                disabled=False
            )
            view.add_item(placeholder_select)
            
            title = "Додавання ролей" if action == "add" else "Видалення ролей"
            description = "Оберіть ролі для додавання до списку заявок:" if action == "add" else "Оберіть ролі для видалення зі списку заявок:"
            
            embed = discord.Embed(
                title=title,
                description=description,
                color=0x2b2d31
            )
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="close_ticket", description="Закрити поточний тікет (тільки модератори)")
    async def close_ticket_command(self, interaction: discord.Interaction):
        """Команда для закриття тікета"""
        
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо права
        if not guild_config["moderator_role_id"] or not any(role.id == guild_config["moderator_role_id"] for role in interaction.user.roles):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        # Перевіряємо чи це тікет канал
        ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
        if not ticket_data:
            await interaction.response.send_message("Ця команда працює тільки в каналах тікетів!", ephemeral=True)
            return
        
        # Створюємо embed для підтвердження
        embed = discord.Embed(
            title="Підтвердження закриття",
            description=f"Ви впевнені що хочете закрити цей тікет?\n\n" +
                       f"Канал: {interaction.channel.mention}\n" +
                       f"Модератор: {interaction.user.mention}\n" +
                       f"Канал буде видалено **безповоротно**",
            color=0xfee75c
        )
        
        view = ConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="ticket_stats", description="Статистика тікетів")
    async def ticket_stats(self, interaction: discord.Interaction):
        """Показує статистику системи тікетів з графіком за 7 днів"""
        
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Підраховуємо активні тікети з бази даних
        active_tickets_cursor = db.tickets.find({
            "guild_id": interaction.guild.id, 
            "status": "open"
        })
        active_tickets = await active_tickets_cursor.to_list(1000)
        
        # Підраховуємо по типам
        tickets_by_type = {}
        for ticket in active_tickets:
            ticket_type = ticket.get("ticket_type", "unknown")
            tickets_by_type[ticket_type] = tickets_by_type.get(ticket_type, 0) + 1
        
        # Отримуємо статистику за 7 днів
        week_stats = await get_week_stats(interaction.guild.id)
        
        embed = discord.Embed(
            title="Статистика системи тікетів",
            description=f"Загальна інформація на {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            color=0x2b2d31,
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="Активні тікети",
            value=f"**{len(active_tickets)}** тікетів відкрито",
            inline=True
        )
        
        category = interaction.guild.get_channel(guild_config["category_id"]) if guild_config["category_id"] else None
        embed.add_field(
            name="Категорія",
            value=category.mention if category else "Не знайдена",
            inline=True
        )
        
        mod_role = interaction.guild.get_role(guild_config["moderator_role_id"]) if guild_config["moderator_role_id"] else None
        embed.add_field(
            name="Модератори",
            value=mod_role.mention if mod_role else "Не налаштовано",
            inline=True
        )
        
        # Графік за 7 днів
        chart_data = ""
        max_count = max([count for _, count in week_stats]) if week_stats else 1
        if max_count == 0:
            max_count = 1
        
        for date, count in week_stats:
            date_formatted = datetime.strptime(date, '%Y-%m-%d').strftime('%d.%m')
            bar_length = int((count / max_count) * 10) if count > 0 else 0
            bar = "█" * bar_length + "░" * (10 - bar_length)
            chart_data += f"`{date_formatted}` {bar} `{count}`\n"
        
        embed.add_field(
            name="Графік відкритих тікетів за 7 днів",
            value=chart_data.strip() if chart_data.strip() else "Немає даних",
            inline=False
        )
        
        # Розбивка по типам тікетів
        if tickets_by_type:
            breakdown = ""
            for ticket_type, count in tickets_by_type.items():
                type_config = TICKET_TYPES.get(ticket_type, {})
                name = type_config.get('name', ticket_type)
                breakdown += f"{name}: **{count}**\n"
            
            embed.add_field(
                name="Розбивка по типам",
                value=breakdown.strip(),
                inline=False
            )
        
        embed.set_footer(text=f"ID сервера: {interaction.guild.id}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="Так, закрити", style=discord.ButtonStyle.danger, custom_id="confirm_close_ticket")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Оновлюємо статус тікета в базі
        await db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {"$set": {"status": "closed", "closed_by": interaction.user.id, "closed_at": datetime.now()}}
        )
        
        embed = discord.Embed(
            title="Тікет закривається",
            description=f"Тікет закрито модератором {interaction.user.mention}\n\n" +
                       f"Час закриття: <t:{int(datetime.now().timestamp())}:F>\n" +
                       f"Канал буде видалено через 10 секунд...",
            color=0xfee75c,
            timestamp=datetime.now()
        )
        embed.set_footer(text="Дякуємо за використання системи тікетів")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Логування закриття
        await self.log_ticket_closure(interaction, guild_config)
        
        # Видаляємо канал через 10 секунд
        await asyncio.sleep(10)
        try:
            await interaction.channel.delete(reason=f"Тікет закрито модератором {interaction.user}")
        except Exception as e:
            print(f"Помилка видалення каналу: {e}")
    
    @discord.ui.button(label="Скасувати", style=discord.ButtonStyle.secondary, custom_id="cancel_close_ticket")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="Скасовано",
            description="Закриття тікета скасовано.",
            color=0x57f287
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def log_ticket_closure(self, interaction: discord.Interaction, guild_config: dict):
        """Логування закриття тікета"""
        if not guild_config["log_channel_id"]:
            return
        
        log_channel = interaction.guild.get_channel(guild_config["log_channel_id"])
        if not log_channel:
            return
        
        try:
            embed = discord.Embed(
                title="Тікет закрито",
                color=0xfee75c,
                timestamp=datetime.now()
            )
            embed.add_field(name="Канал", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
            embed.add_field(name="Час закриття", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
            
            await log_channel.send(embed=embed)
        except:
            pass
    
    async def on_timeout(self):
        # Відключаємо кнопки після таймауту
        for item in self.children:
            item.disabled = True

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    print("Ticket System з базою даних завантажено")=view)
            return
        
        role_id_str = self.values[0]
        
        if role_id_str == "no_roles":
            await interaction.response.send_message("Немає доступних ролей для заявки!", ephemeral=True)
            return
        
        role_id = int(role_id_str)
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("Роль не знайдена!", ephemeral=True)
            return
        
        # Перевіряємо чи вже має роль
        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"У вас вже є роль {role.mention}!", 
                ephemeral=True
            )
            return
        
        # Створюємо тікет для заявки на роль
        ticket_select = TicketTypeSelect()
        await ticket_select.create_ticket(interaction, "role_application", role_id)

class TicketMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

class RoleSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild = None, available_roles: list = None):
        super().__init__(timeout=600)  # 10 хвилин
        if guild and available_roles is not None:
            options = []
            
            # Сортуємо за позицією (вищі ролі першими)
            available_roles.sort(key=lambda r: r.position, reverse=True)
            
            # Беремо перші 25 ролей (обмеження Discord)
            for role in available_roles[:25]:
                options.append(
                    discord.SelectOption(
                        label=role.name,
                        description=f"Подати заявку на роль {role.name}",
                        value=str(role.id)
                    )
                )
            
            if not options:
                options.append(
                    discord.SelectOption(
                        label="Немає доступних ролей",
                        description="Зверніться до адміністрації",
                        value="no_roles"
                    )
                )
            
            select = discord.ui.Select(
                placeholder="Оберіть роль...",
                options=options,
                min_values=1,
                max_values=1
            )
            
            async def select_callback(select_interaction):
                role_id_str = select.values[0]
                
                if role_id_str == "no_roles":
                    await select_interaction.response.send_message("Немає доступних ролей для заявки!", ephemeral=True)
                    return
                
                role_id = int(role_id_str)
                role = select_interaction.guild.get_role(role_id)
                
                if not role:
                    await select_interaction.response.send_message("Роль не знайдена!", ephemeral=True)
                    return
                
                # Перевіряємо чи вже має роль
                if role in select_interaction.user.roles:
                    await select_interaction.response.send_message(
                        f"У вас вже є роль {role.mention}!", 
                        ephemeral=True
                    )
                    return
                
                # Створюємо тікет для заявки на роль
                ticket_select = TicketTypeSelect()
                await ticket_select.create_ticket(select_interaction, "role_application", role_id)
            
            select.callback = select_callback
            self.add_item(select)

class RoleApplicationButtons(discord.ui.View):
    def __init__(self, role_id: int = None, user_id: int = None, channel_id: int = None):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.user_id = user_id
        self.channel_id = channel_id
    
    @discord.ui.button(label="Схвалити заявку", style=discord.ButtonStyle.green, custom_id="approve_role_application")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо права
        if not guild_config["moderator_role_id"] or not any(role.id == guild_config["moderator_role_id"] for role in interaction.user.roles):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        # Отримуємо дані з бази якщо не передано
        if not self.role_id or not self.user_id:
            ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
            if ticket_data:
                self.role_id = ticket_data.get("role_id")
                self.user_id = ticket_data.get("user_id")
        
        if not self.role_id or not self.user_id:
            await interaction.response.send_message("Дані тікета не знайдено в базі даних. Використайте /close_ticket", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        if not user:
            await interaction.response.send_message("Користувач не знайдений на сервері!", ephemeral=True)
            return
        
        # Знаходимо роль
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("Роль не знайдена!", ephemeral=True)
            return
        
        try:
            await user.add_roles(role, reason=f"Схвалено модератором {interaction.user}")
            
            # Оновлюємо статус тікета в базі
            await db.tickets.update_one(
                {"channel_id": interaction.channel.id},
                {"$set": {"status": "approved", "approved_by": interaction.user.id, "approved_at": datetime.now()}}
            )
            
            # Повідомлення в тікеті
            embed = discord.Embed(
                title="Заявку схвалено",
                description=f"**Користувач:** {user.mention}\n**Роль:** {role.mention}\n**Модератор:** {interaction.user.mention}",
                color=0x57f287,
                timestamp=datetime.now()
            )
            embed.add_field(
                name="Вітаємо",
                value=f"Роль **{role.name}** успішно додано до профілю користувача",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=TicketCloseView())
            
            # DM користувачу
            try:
                dm_embed = discord.Embed(
                    title="Заявку схвалено",
                    description=f"Вашу заявку на роль **{role.name}** схвалено\n\n" +
                               f"Сервер: **{interaction.guild.name}**\n" +
                               f"Роль додано до вашого профілю\n" +
                               f"Модератор: {interaction.user.mention}",
                    color=0x57f287
                )
                await user.send(embed=dm_embed)
            except:
                # Якщо не може відправити DM - повідомляємо в каналі
                await interaction.followup.send(
                    f"{user.mention}, не вдалося відправити повідомлення в ПП. " +
                    f"Ваша заявка схвалена і роль {role.mention} додано!",
                    ephemeral=False
                )
            
        except Exception as e:
            await interaction.response.send_message(f"Помилка додавання ролі: {e}", ephemeral=True)
    
    @discord.ui.button(label="Відхилити заявку", style=discord.ButtonStyle.red, custom_id="reject_role_application")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо права
        if not guild_config["moderator_role_id"] or not any(role.id == guild_config["moderator_role_id"] for role in interaction.user.roles):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        # Отримуємо дані з бази якщо не передано
        if not self.role_id or not self.user_id:
            ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
            if ticket_data:
                self.role_id = ticket_data.get("role_id")
                self.user_id = ticket_data.get("user_id")
        
        # Modal для причини відхилення
        modal = RejectModal(self.role_id, self.user_id, interaction.channel.id)
        await interaction.response.send_modal(modal)

class GeneralTicketButtons(discord.ui.View):
    def __init__(self, ticket_type: str = None, user_id: int = None, channel_id: int = None):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.user_id = user_id
        self.channel_id = channel_id
    
    @discord.ui.button(label="Вирішено", style=discord.ButtonStyle.green, custom_id="resolve_general_ticket")
    async def resolve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо права
        if not guild_config["moderator_role_id"] or not any(role.id == guild_config["moderator_role_id"] for role in interaction.user.roles):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        # Отримуємо дані з бази якщо не передано
        if not self.ticket_type or not self.user_id:
            ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
            if ticket_data:
                self.ticket_type = ticket_data.get("ticket_type")
                self.user_id = ticket_data.get("user_id")
        
        if not self.ticket_type or not self.user_id:
            await interaction.response.send_message("Дані тікета не знайдено в базі даних.", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        config = TICKET_TYPES.get(self.ticket_type, {"name": "Невідомий тип"})
        
        # Оновлюємо статус тікета в базі
        await db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {"$set": {"status": "resolved", "resolved_by": interaction.user.id, "resolved_at": datetime.now()}}
        )
        
        embed = discord.Embed(
            title="Тікет вирішено",
            description=f"**Користувач:** {user.mention if user else 'Користувач покинув сервер'}\n" +
                       f"**Тип тікета:** {config['name']}\n" +
                       f"**Модератор:** {interaction.user.mention}",
            color=0x57f287,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="Статус",
            value="Тікет успішно вирішено та готовий до закриття",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view