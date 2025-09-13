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
        "emoji": "<:odym:1412519796456689714>",
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
        "emoji": "<:dva:1412519805185163274>",
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
        "emoji": "<:try:1412519816245547038>",
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
        "emoji": "<:chetyri:1412519826274127973>",
        "questions": [
            "Опишіть ваше питання або проблему:",
            "Чи намагались ви вирішити це самостійно?",
            "Додаткові деталі:"
        ]
    },
    "complaint": {
        "name": "Скарга",
        "description": "Подати скаргу на користувача або ситуацію",
        "emoji": "<:pyat:1412519858960339064>",
        "questions": [
            "На кого або що ви скаржитесь?",
            "Що сталося? Опишіть ситуацію:",
            "Чи є у вас докази (скріншоти, повідомлення)?",
            "Додаткова інформація:"
        ]
    }
}

# Утилітні функції
async def get_guild_config(guild_id: int):
    config = await db.ticket_config.find_one({"guild_id": guild_id})
    if not config:
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
    await db.ticket_config.update_one(
        {"guild_id": guild_id},
        {"$set": updates},
        upsert=True
    )

async def save_ticket_stat(guild_id: int):
    today = datetime.now().strftime('%Y-%m-%d')
    await db.ticket_stats.update_one(
        {"guild_id": guild_id, "date": today},
        {"$inc": {"count": 1}},
        upsert=True
    )

async def get_week_stats(guild_id: int):
    stats = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6-i)).strftime('%Y-%m-%d')
        stat = await db.ticket_stats.find_one({"guild_id": guild_id, "date": date})
        count = stat["count"] if stat else 0
        stats.append((date, count))
    return stats

def has_moderator_permissions(interaction: discord.Interaction, guild_config: dict) -> bool:
    """Перевіряє чи має користувач права модератора"""
    if not guild_config.get("moderator_role_id"):
        return interaction.user.guild_permissions.administrator
    return any(role.id == guild_config["moderator_role_id"] for role in interaction.user.roles)

async def send_dm_notification(user: discord.Member, embed: discord.Embed):
    """Відправляє DM користувачу"""
    try:
        await user.send(embed=embed)
    except:
        pass

async def log_ticket_action(guild: discord.Guild, guild_config: dict, embed: discord.Embed):
    """Логування дій з тікетами"""
    if not guild_config.get("log_channel_id"):
        return
    log_channel = guild.get_channel(guild_config["log_channel_id"])
    if log_channel:
        try:
            await log_channel.send(embed=embed)
        except:
            pass

# Views and Modals
class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for ticket_type, config in TICKET_TYPES.items():
            options.append(
                discord.SelectOption(
                    label=config["name"],
                    description=config["description"], 
                    value=ticket_type,
                    emoji=config["emoji"]
                )
            )
        
        super().__init__(
            placeholder="Оберіть тип тікета...",
            options=options,
            custom_id="ticket_type_select_main"
        )
    
    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        guild_config = await get_guild_config(interaction.guild.id)
        
        if ticket_type == "role_application":
            if not guild_config["available_roles"]:
                await interaction.response.send_message(
                    "Адміністратори ще не налаштували доступні ролі для заявок.", 
                    ephemeral=True
                )
                return
            
            available_roles = [interaction.guild.get_role(role_id) 
                             for role_id in guild_config["available_roles"]]
            available_roles = [role for role in available_roles if role and not role.is_bot_managed()]
            
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
            await self.create_ticket(interaction, ticket_type)
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, role_id: int = None):
        config = TICKET_TYPES[ticket_type]
        guild_config = await get_guild_config(interaction.guild.id)
        
        # Перевіряємо чи вже є відкритий тікет
        existing_ticket = await db.tickets.find_one({
            "guild_id": interaction.guild.id,
            "user_id": interaction.user.id,
            "ticket_type": ticket_type,
            "status": "open"
        })
        
        if existing_ticket:
            channel = interaction.guild.get_channel(existing_ticket["channel_id"])
            if channel:
                await interaction.response.send_message(
                    f"У вас вже є відкритий тікет: {channel.mention}",
                    ephemeral=True
                )
                return
        
        # Створення каналу
        category = await self.get_or_create_category(interaction.guild, guild_config)
        if not category:
            await interaction.response.send_message(
                "Не вдалося створити категорію для тікетів", 
                ephemeral=True
            )
            return
        
        # Назва тікета (спрощена)
        if role_id:
            role = interaction.guild.get_role(role_id)
            ticket_name = f"роль-{role.name if role else 'unknown'}"
        else:
            config_name = config['name'].lower().replace(' ', '-')
            ticket_name = config_name
        
        ticket_name = f"{ticket_name}-{interaction.user.id}"[:50]
        
        # Права доступу
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(
                read_messages=True, send_messages=True, attach_files=True, embed_links=True
            ),
        }
        
        if guild_config["moderator_role_id"]:
            mod_role = interaction.guild.get_role(guild_config["moderator_role_id"])
            if mod_role:
                overwrites[mod_role] = discord.PermissionOverwrite(
                    read_messages=True, send_messages=True, manage_messages=True,
                    attach_files=True, embed_links=True
                )
        
        try:
            channel = await category.create_text_channel(
                name=ticket_name.lower().replace(" ", "-"),
                overwrites=overwrites
            )
            
            # Збереження в базу
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
            
            # Основне повідомлення
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
            
            embed.set_footer(text=f"ID користувача: {interaction.user.id}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Вибір view
            if ticket_type == "role_application":
                view = RoleApplicationButtons(role_id, interaction.user.id, channel.id)
            else:
                view = GeneralTicketButtons(ticket_type, interaction.user.id, channel.id)
            
            # Відправлення повідомлення
            mod_role = interaction.guild.get_role(guild_config["moderator_role_id"]) if guild_config["moderator_role_id"] else None
            await channel.send(
                f"{interaction.user.mention}{' | ' + mod_role.mention if mod_role else ''}",
                embed=embed,
                view=view
            )
            
            # Питання
            await self.ask_questions(channel, config['questions'])
            
            # Статистика
            await save_ticket_stat(interaction.guild.id)
            
            # Відповідь користувачу
            success_embed = discord.Embed(
                title="Тікет успішно створено",
                description=f"**Ваш тікет:** {channel.mention}\n\n" +
                           f"Тип: {config['name']}\n" +
                           f"Очікуйте відповіді від модерації",
                color=0x57f287
            )
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=success_embed, view=None)
            else:
                await interaction.response.send_message(embed=success_embed, view=None, ephemeral=True)
            
            # Лог
            log_embed = discord.Embed(
                title="Новий тікет створено",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            log_embed.add_field(name="Користувач", value=f"{interaction.user.mention} (`{interaction.user.id}`)", inline=True)
            log_embed.add_field(name="Тип", value=config['name'], inline=True)
            log_embed.add_field(name="Канал", value=channel.mention, inline=True)
            log_embed.set_thumbnail(url=interaction.user.display_avatar.url)
            await log_ticket_action(interaction.guild, guild_config, log_embed)
            
        except Exception as e:
            error_message = f"Помилка створення тікета: {e}"
            if interaction.response.is_done():
                await interaction.edit_original_response(content=error_message, embed=None, view=None)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
    
    async def get_or_create_category(self, guild: discord.Guild, guild_config: dict):
        """Знаходить або створює категорію для тікетів"""
        if guild_config["category_id"]:
            category = guild.get_channel(guild_config["category_id"])
            if category:
                return category
        
        for cat in guild.categories:
            if cat.name.lower() in ["tickets", "тікети", "тикеты"]:
                await update_guild_config(guild.id, {"category_id": cat.id})
                return cat
        
        try:
            category = await guild.create_category("Тікети")
            await update_guild_config(guild.id, {"category_id": category.id})
            return category
        except:
            return None
    
    async def ask_questions(self, channel: discord.TextChannel, questions: list):
        """Задає питання користувачу"""
        await asyncio.sleep(3)
        
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
        
        await channel.send(embed=questions_embed)

class RoleSelectView(discord.ui.View):
    def __init__(self, guild: discord.Guild, available_roles: list):
        super().__init__(timeout=600)
        
        options = []
        available_roles.sort(key=lambda r: r.position, reverse=True)
        
        for role in available_roles[:25]:
            options.append(
                discord.SelectOption(
                    label=role.name,
                    description=f"Подати заявку на роль {role.name}",
                    value=str(role.id)
                )
            )
        
        select = discord.ui.Select(
            placeholder="Оберіть роль...",
            options=options
        )
        
        async def select_callback(select_interaction):
            role_id = int(select.values[0])
            role = select_interaction.guild.get_role(role_id)
            
            if not role or role in select_interaction.user.roles:
                await select_interaction.response.send_message(
                    f"{'Роль не знайдена!' if not role else f'У вас вже є роль {role.mention}!'}", 
                    ephemeral=True
                )
                return
            
            ticket_select = TicketTypeSelect()
            await ticket_select.create_ticket(select_interaction, "role_application", role_id)
        
        select.callback = select_callback
        self.add_item(select)

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
        embed.add_field(name="Причина відхилення", value=self.reason.value, inline=False)
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            dm_embed = discord.Embed(
                title="<:palka:1412777364387135589> Заявку відхилено",
                description=f"На жаль, вашу заявку на роль **{role.name if role else 'невідома роль'}** відхилено.\n\n" +
                           f"**Сервер:** {interaction.guild.name}\n" +
                           f"**Причина:** {self.reason.value}\n\n" +
                           f"Ви можете подати нову заявку пізніше",
                color=0xed4245,
                timestamp=datetime.now()
            )
            await send_dm_notification(user, dm_embed)

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="Закрити тікет", style=discord.ButtonStyle.secondary, custom_id="close_ticket_final")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        if not has_moderator_permissions(interaction, guild_config):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
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
        
        # Лог
        log_embed = discord.Embed(
            title="Тікет закрито",
            color=0xfee75c,
            timestamp=datetime.now()
        )
        log_embed.add_field(name="Канал", value=f"#{interaction.channel.name}", inline=True)
        log_embed.add_field(name="Модератор", value=interaction.user.mention, inline=True)
        await log_ticket_action(interaction.guild, guild_config, log_embed)
        
        await asyncio.sleep(15)
        try:
            await interaction.channel.delete(reason=f"Тікет закрито модератором {interaction.user}")
        except:
            pass

class RoleApplicationButtons(discord.ui.View):
    def __init__(self, role_id: int = None, user_id: int = None, channel_id: int = None):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.user_id = user_id
        self.channel_id = channel_id
    
    @discord.ui.button(label="Схвалити заявку", style=discord.ButtonStyle.green, custom_id="approve_role_application")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        if not has_moderator_permissions(interaction, guild_config):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        # Отримуємо дані з бази якщо потрібно
        if not all([self.role_id, self.user_id]):
            ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
            if ticket_data:
                self.role_id = ticket_data.get("role_id")
                self.user_id = ticket_data.get("user_id")
        
        user = interaction.guild.get_member(self.user_id)
        role = interaction.guild.get_role(self.role_id)
        
        if not user or not role:
            await interaction.response.send_message("Користувач або роль не знайдені!", ephemeral=True)
            return
        
        try:
            await user.add_roles(role, reason=f"Схвалено модератором {interaction.user}")
            
            await db.tickets.update_one(
                {"channel_id": interaction.channel.id},
                {"$set": {"status": "approved", "approved_by": interaction.user.id, "approved_at": datetime.now()}}
            )
            
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
            dm_embed = discord.Embed(
                title="<:palka:1412777364387135589> Заявку схвалено",
                description=f"Вашу заявку на роль **{role.name}** схвалено\n\n" +
                           f"**Сервер:** {interaction.guild.name}\n" +
                           f"**Модератор:** {interaction.user.mention}\n\n" +
                           f"Роль додано до вашого профілю",
                color=0x57f287,
                timestamp=datetime.now()
            )
            await send_dm_notification(user, dm_embed)
            
        except Exception as e:
            await interaction.response.send_message(f"Помилка додавання ролі: {e}", ephemeral=True)
    
    @discord.ui.button(label="Відхилити заявку", style=discord.ButtonStyle.red, custom_id="reject_role_application")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        guild_config = await get_guild_config(interaction.guild.id)
        
        if not has_moderator_permissions(interaction, guild_config):
            await interaction.response.send_message("Недостатньо прав!", ephemeral=True)
            return
        
        if not all([self.role_id, self.user_id]):
            ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
            if ticket_data:
                self.role_id = ticket_data.get("role_id")
                self.user_id = ticket_data.get("user_id")
        
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
        # Дозволяємо всім користувачам закривати загальні тікети
        if not all([self.ticket_type, self.user_id]):
            ticket_data = await db.tickets.find_one({"channel_id": interaction.channel.id})
            if ticket_data:
                self.ticket_type = ticket_data.get("ticket_type")
                self.user_id = ticket_data.get("user_id")
        
        user = interaction.guild.get_member(self.user_id)
        config = TICKET_TYPES.get(self.ticket_type, {"name": "Невідомий тип"})
        
        await db.tickets.update_one(
            {"channel_id": interaction.channel.id},
            {"$set": {"status": "resolved", "resolved_by": interaction.user.id, "resolved_at": datetime.now()}}
        )
        
        embed = discord.Embed(
            title="Тікет вирішено",
            description=f"**Користувач:** {user.mention if user else 'Користувач покинув сервер'}\n" +
                       f"**Тип тікета:** {config['name']}\n" +
                       f"**Вирішив:** {interaction.user.mention}",
            color=0x57f287,
            timestamp=datetime.now()
        )
        embed.add_field(
            name="Статус",
            value="Тікет успішно вирішено та готовий до закриття",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            dm_embed = discord.Embed(
                title="<:palka:1412777364387135589> Тікет вирішено",
                description=f"Ваш тікет типу **{config['name']}** було вирішено.\n\n" +
                           f"**Сервер:** {interaction.guild.name}\n" +
                           f"**Вирішив:** {interaction.user.mention}\n\n" +
                           f"Дякуємо за звернення!",
                color=0x57f287,
                timestamp=datetime.now()
            )
            await send_dm_notification(user, dm_embed)

class TicketMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        self.bot.add_view(TicketMainView())
        self.bot.add_view(RoleApplicationButtons())
        self.bot.add_view(GeneralTicketButtons())
        self.bot.add_view(TicketCloseView())
    
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
        app_commands.Choice(name="Показати поточні налаштування", value="show_config"),
        app_commands.Choice(name="Додати ролі", value="add_roles"),
        app_commands.Choice(name="Видалити ролі", value="remove_roles"),
        app_commands.Choice(name="Показати ролі", value="list_roles")
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
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Тільки адміністратори можуть використовувати цю команду!", ephemeral=True)
            return
        
        guild_config = await get_guild_config(interaction.guild.id)
        
        if action == "create_panel":
            target_channel = channel or interaction.channel
            
            # Головний embed з емодзі
            main_embed = discord.Embed(
                title="<:palka:1412777364387135589> Правила мероприятій",
                color=0x2b2d31,
                timestamp=datetime.now()
            )
            
            # Додаємо правила
            rules_text = (
                "**1.** Дотримуйтесь всіх правил сервера на мероприятіях.\n"
                "**2.** Заборонено заважати проведенню мероприятія або створювати помехи.\n"
                "**3.** Дотримуйтесь правил, встановлених для конкретного мероприятія.\n"
                "**4.** Ігнорування ведучого мероприятія недопустиме.\n"
                "**5.** Кидати мероприятіє без поважної причини заборонено."
            )
            
            main_embed.add_field(
                name="<:palka:1412777364387135589> • Правила мероприятій :",
                value=rules_text,
                inline=False
            )
            
            # Примітки
            notes_text = (
                "**—** Покарання видається по розсуду ведучого конкретного мероприятія.\n\n"
                "**—** За порушення на мероприятіях ви получите роль @Ban | Event, яка обмежує участь у майбутніх мероприятіях.\n\n"
                "**—** Якщо ви помітили порушення з боку @Host під час мероприятія, подайте жалобу через кнопку в анонсах # 📢 • анонсы.\n\n"
                "**—** Щоб получити інформацію про потрібне вам мероприятіє, використовуйте меню нижче повідомлення."
            )
            
            main_embed.add_field(
                name="<:palka:1412777364387135589> • Примітки :",
                value=notes_text,
                inline=False
            )
            
            view = TicketMainView()
            await target_channel.send(embed=main_embed, view=view)
            
            success_embed = discord.Embed(
                title="Панель тікетів створено",
                description=f"Панель успішно розміщено в {target_channel.mention}",
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
            embed = discord.Embed(title="Поточні налаштування", color=0x2b2d31)
            
            mod_role = interaction.guild.get_role(guild_config["moderator_role_id"]) if guild_config["moderator_role_id"] else None
            log_channel = interaction.guild.get_channel(guild_config["log_channel_id"]) if guild_config["log_channel_id"] else None
            category = interaction.guild.get_channel(guild_config["category_id"]) if guild_config["category_id"] else None
            
            embed.add_field(name="Роль модераторів", value=mod_role.mention if mod_role else "Не налаштовано", inline=True)
            embed.add_field(name="Канал логів", value=log_channel.mention if log_channel else "Не налаштовано", inline=True)
            embed.add_field(name="Категорія", value=category.name if category else "Не налаштовано", inline=True)
            embed.add_field(name="Кількість ролей", value=f"{len(guild_config['available_roles'])} ролей", inline=True)
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        elif action in ["add_roles", "remove_roles", "list_roles"]:
            await self.manage_roles_action(interaction, action, guild_config)
    
    async def manage_roles_action(self, interaction: discord.Interaction, action: str, guild_config: dict):
        if action == "list_roles":
            if not guild_config["available_roles"]:
                embed = discord.Embed(
                    title="Список ролей",
                    description="Немає налаштованих ролей для заявок",
                    color=0xed4245
                )
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            embed = discord.Embed(title="Доступні ролі для заявок", color=0x2b2d31)
            
            roles_list = []
            valid_roles = []
            for i, role_id in enumerate(guild_config["available_roles"], 1):
                role = interaction.guild.get_role(role_id)
                if role:
                    roles_list.append(f"{i}. {role.mention}")
                    valid_roles.append(role_id)
                else:
                    roles_list.append(f"{i}. Роль видалена (ID: {role_id})")
            
            if len(valid_roles) != len(guild_config["available_roles"]):
                await update_guild_config(interaction.guild.id, {"available_roles": valid_roles})
            
            embed.add_field(
                name=f"Ролей: {len(valid_roles)}",
                value="\n".join(roles_list) if roles_list else "Немає ролей",
                inline=False
            )
            
            await interaction.response.send_message(embed=embed, ephemeral=True)
        
        else:
            view = MultiRoleView(interaction.guild, action.replace("_roles", ""))
            title = "Додавання ролей" if action == "add_roles" else "Видалення ролей"
            description = "Оберіть ролі для додавання до списку заявок:" if action == "add_roles" else "Оберіть ролі для видалення зі списку заявок:"
            
            embed = discord.Embed(title=title, description=description, color=0x2b2d31)
            
            # Створюємо select з ролями
            options = []
            if action == "add_roles":
                for role in interaction.guild.roles:
                    if (role != interaction.guild.default_role and 
                        not role.is_bot_managed() and 
                        role.id != guild_config.get("moderator_role_id") and
                        not role.permissions.administrator and
                        not role.permissions.manage_guild and
                        role.id not in guild_config["available_roles"]):
                        options.append(discord.SelectOption(label=role.name[:100], value=str(role.id)))
            else:
                for role_id in guild_config["available_roles"]:
                    role = interaction.guild.get_role(role_id)
                    if role:
                        options.append(discord.SelectOption(label=role.name[:100], value=str(role.id)))
            
            if not options:
                text = "Немає ролей для додавання" if action == "add_roles" else "Немає ролей для видалення"
                embed.description = text
                await interaction.response.send_message(embed=embed, ephemeral=True)
                return
            
            select = MultiRoleSelect(interaction.guild, action.replace("_roles", ""), guild_config, options[:25])
            view = discord.ui.View(timeout=300)
            view.add_item(select)
            
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

class MultiRoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild, mode: str, guild_config: dict, options: list):
        self.guild = guild
        self.mode = mode
        self.guild_config = guild_config
        
        if not options:
            options = [discord.SelectOption(label="Немає доступних ролей", value="no_roles")]
        
        placeholder = "Оберіть ролі для додавання..." if mode == "add" else "Оберіть ролі для видалення..."
        
        super().__init__(
            placeholder=placeholder,
            options=options,
            min_values=1,
            max_values=min(len(options), 25)
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
            else:
                if role_id in self.guild_config["available_roles"]:
                    self.guild_config["available_roles"].remove(role_id)
                    changed_roles.append(f"- {role.mention}")
        
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

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    print("Ticket System завантажено")