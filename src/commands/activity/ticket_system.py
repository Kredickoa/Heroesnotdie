import discord
from discord import app_commands
from discord.ext import commands
from datetime import datetime
import asyncio
import json
from typing import Optional

# Конфігурація
CONFIG = {
    "MODERATOR_ROLE_ID": 123456789012345678,  # ID ролі модераторів
    "CATEGORY_ID": None,                      # Буде знайдено автоматично або створено
    "LOG_CHANNEL_ID": 123456789012345678,     # ID каналу логів (опціонально)
    
    # Ролі які можна отримати через заявку (залиште пустим щоб показати всі ролі сервера)
    "AVAILABLE_ROLES": [
        # 123456789012345678,  # ID ролі 1
        # 123456789012345678,  # ID ролі 2
    ]
}

# Типи тікетів
TICKET_TYPES = {
    "role_application": {
        "name": "🎭 Заявка на роль",
        "emoji": "🎭",
        "description": "Подати заявку на отримання ролі",
        "questions": [
            "Чому ви хочете отримати цю роль?",
            "Чи маєте ви досвід, пов'язаний з цією роллю?",
            "Як ви плануєте використовувати цю роль?",
            "Додаткова інформація про себе:"
        ]
    },
    "server_suggestion": {
        "name": "💡 Пропозиція для сервера",
        "emoji": "💡", 
        "description": "Поділитися ідеями для покращення сервера",
        "questions": [
            "Яка ваша пропозиція?",
            "Як це покращить сервер?",
            "Чи розглядали ви можливі недоліки?",
            "Додаткові деталі або коментарі:"
        ]
    },
    "bug_report": {
        "name": "🐛 Звіт про баг",
        "emoji": "🐛",
        "description": "Повідомити про технічні проблеми",
        "questions": [
            "Опишіть проблему детально:",
            "Як відтворити цю помилку?",
            "Що ви очікували побачити?",
            "Додаткова інформація (скріншоти, логи):"
        ]
    },
    "general_support": {
        "name": "❓ Загальна підтримка",
        "emoji": "❓",
        "description": "Питання або допомога від модерації",
        "questions": [
            "Опишіть ваше питання або проблему:",
            "Чи намагались ви вирішити це самостійно?",
            "Додаткові деталі:"
        ]
    },
    "complaint": {
        "name": "⚠️ Скарга",
        "emoji": "⚠️",
        "description": "Подати скаргу на користувача або ситуацію",
        "questions": [
            "На кого або що ви скаржитесь?",
            "Що сталося? Опишіть ситуацію:",
            "Чи є у вас докази (скріншоти, повідомлення)?",
            "Додаткова інформація:"
        ]
    }
}

class TicketTypeSelect(discord.ui.Select):
    def __init__(self):
        options = []
        for ticket_type, config in TICKET_TYPES.items():
            options.append(
                discord.SelectOption(
                    label=config["name"],
                    description=config["description"], 
                    emoji=config["emoji"],
                    value=ticket_type
                )
            )
        
        super().__init__(
            placeholder="🎫 Оберіть тип тікета...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="ticket_type_select_main"
        )
    
    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        
        if ticket_type == "role_application":
            # Якщо це заявка на роль - показуємо вибір ролей
            view = RoleSelectView(interaction.guild)
            embed = discord.Embed(
                title="🎭 Заявка на роль",
                description="Оберіть роль, на яку хочете подати заявку:",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # Для інших типів - відразу створюємо тікет
            await self.create_ticket(interaction, ticket_type)
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, role_id: int = None):
        config = TICKET_TYPES[ticket_type]
        
        # Перевіряємо чи вже є відкритий тікет
        existing_ticket = None
        for channel in interaction.guild.text_channels:
            if (channel.name.startswith(ticket_type) and 
                str(interaction.user.id) in channel.name):
                existing_ticket = channel
                break
        
        if existing_ticket:
            await interaction.response.send_message(
                f"❌ У вас вже є відкритий тікет: {existing_ticket.mention}",
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
        if CONFIG["CATEGORY_ID"]:
            category = interaction.guild.get_channel(CONFIG["CATEGORY_ID"])
        
        if not category:
            # Шукаємо категорію з назвою "Tickets" або створюємо нову
            for cat in interaction.guild.categories:
                if cat.name.lower() in ["tickets", "тікети", "тикеты"]:
                    category = cat
                    CONFIG["CATEGORY_ID"] = cat.id
                    break
            
            if not category:
                try:
                    category = await interaction.guild.create_category("🎫 Тікети")
                    CONFIG["CATEGORY_ID"] = category.id
                except Exception as e:
                    await interaction.response.send_message(
                        f"❌ Не вдалося створити категорію для тікетів: {e}", 
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
        mod_role = interaction.guild.get_role(CONFIG["MODERATOR_ROLE_ID"])
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
            
            # Embed з інформацією
            embed = discord.Embed(
                title=f"{config['emoji']} {config['name']}",
                description=f"**Користувач:** {interaction.user.mention}\n**Створено:** <t:{int(datetime.now().timestamp())}:F>",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            
            if role_id:
                role = interaction.guild.get_role(role_id)
                embed.add_field(
                    name="🎯 Запитувана роль",
                    value=f"{role.mention if role else 'Невідома роль'}",
                    inline=True
                )
            
            embed.add_field(
                name="📋 Інструкції",
                value="• Відповідайте на запитання чесно та детально\n• Очікуйте відповіді від модерації\n• Не спамте в каналі",
                inline=False
            )
            
            embed.set_footer(text=f"ID користувача: {interaction.user.id}")
            embed.set_thumbnail(url=interaction.user.display_avatar.url)
            
            # Створюємо view з кнопками для модерації
            if ticket_type == "role_application":
                view = RoleApplicationButtons(role_id, interaction.user.id)
            else:
                view = GeneralTicketButtons(ticket_type, interaction.user.id)
            
            # Відправляємо повідомлення
            message = await channel.send(
                f"👋 {interaction.user.mention} | 🛡️ {mod_role.mention if mod_role else '@Модерація'}\n" +
                f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
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
            
            # Відповідь користувачу
            success_embed = discord.Embed(
                title="✅ Тікет успішно створено!",
                description=f"**Ваш тікет:** {channel.mention}\n\n" +
                           f"🔹 Тип: {config['name']}\n" +
                           f"🔹 Очікуйте відповіді від модерації\n" +
                           f"🔹 Не закривайте цю вкладку до завершення",
                color=discord.Color.green()
            )
            success_embed.set_footer(text="Дякуємо за звернення!")
            
            if interaction.response.is_done():
                await interaction.edit_original_response(embed=success_embed, view=None)
            else:
                await interaction.response.edit_message(embed=success_embed, view=None)
            
            # Лог у канал логів
            await self.log_ticket_creation(interaction.guild, interaction.user, config, channel)
            
        except Exception as e:
            error_message = f"❌ Помилка створення тікета: {e}"
            if interaction.response.is_done():
                await interaction.edit_original_response(content=error_message, embed=None, view=None)
            else:
                await interaction.response.send_message(error_message, ephemeral=True)
    
    async def ask_questions(self, channel: discord.TextChannel, questions: list, user: discord.Member):
        """Задає питання користувачу"""
        await asyncio.sleep(3)  # Невелика затримка
        
        questions_embed = discord.Embed(
            title="📝 Анкета",
            description="Будь ласка, дайте відповіді на наступні питання:",
            color=discord.Color.blue()
        )
        
        for i, question in enumerate(questions, 1):
            questions_embed.add_field(
                name=f"❓ Питання {i}",
                value=question,
                inline=False
            )
        
        questions_embed.set_footer(text="Відповідайте по одному питанню в повідомленні")
        await channel.send(embed=questions_embed)
    
    async def log_ticket_creation(self, guild: discord.Guild, user: discord.Member, config: dict, channel: discord.TextChannel):
        """Логування створення тікета"""
        if not CONFIG["LOG_CHANNEL_ID"]:
            return
        
        log_channel = guild.get_channel(CONFIG["LOG_CHANNEL_ID"])
        if not log_channel:
            return
        
        try:
            embed = discord.Embed(
                title="🎫 Новий тікет створено",
                color=discord.Color.blue(),
                timestamp=datetime.now()
            )
            embed.add_field(name="👤 Користувач", value=f"{user.mention} (`{user.id}`)", inline=True)
            embed.add_field(name="📋 Тип", value=config['name'], inline=True)
            embed.add_field(name="📍 Канал", value=channel.mention, inline=True)
            embed.set_thumbnail(url=user.display_avatar.url)
            
            await log_channel.send(embed=embed)
        except:
            pass

class RoleSelect(discord.ui.Select):
    def __init__(self, guild: discord.Guild):
        self.guild = guild
        options = []
        
        # Отримуємо ролі сервера
        available_roles = []
        if CONFIG["AVAILABLE_ROLES"]:
            # Якщо задані конкретні ролі
            for role_id in CONFIG["AVAILABLE_ROLES"]:
                role = guild.get_role(role_id)
                if role and not role.is_bot_managed():
                    available_roles.append(role)
        else:
            # Показуємо всі ролі крім @everyone, ботів та модераторів
            for role in guild.roles:
                if (role != guild.default_role and 
                    not role.is_bot_managed() and 
                    role.id != CONFIG["MODERATOR_ROLE_ID"] and
                    not role.permissions.administrator and
                    not role.permissions.manage_guild):
                    available_roles.append(role)
        
        # Сортуємо за позицією (вищі ролі першими)
        available_roles.sort(key=lambda r: r.position, reverse=True)
        
        # Беремо перші 25 ролей (обмеження Discord)
        for role in available_roles[:25]:
            options.append(
                discord.SelectOption(
                    label=role.name,
                    description=f"Подати заявку на роль {role.name}",
                    emoji="🎭",
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
        
        super().__init__(
            placeholder="🎭 Оберіть роль...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="role_select_application"
        )
    
    async def callback(self, interaction: discord.Interaction):
        role_id_str = self.values[0]
        
        if role_id_str == "no_roles":
            await interaction.response.send_message("❌ Немає доступних ролей для заявки!", ephemeral=True)
            return
        
        role_id = int(role_id_str)
        role = interaction.guild.get_role(role_id)
        
        if not role:
            await interaction.response.send_message("❌ Роль не знайдена!", ephemeral=True)
            return
        
        # Перевіряємо чи вже має роль
        if role in interaction.user.roles:
            await interaction.response.send_message(
                f"❌ У вас вже є роль {role.mention}!", 
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
    def __init__(self, guild: discord.Guild = None):
        super().__init__(timeout=600)  # 10 хвилин
        if guild:
            self.add_item(RoleSelect(guild))

class RoleApplicationButtons(discord.ui.View):
    def __init__(self, role_id: int = None, user_id: int = None):
        super().__init__(timeout=None)
        self.role_id = role_id
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Схвалити заявку", style=discord.ButtonStyle.green, custom_id="approve_role_application")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        # Якщо немає збережених даних
        if not self.role_id or not self.user_id:
            await interaction.response.send_message("❌ Дані тікета втрачено. Використайте /close_ticket", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        if not user:
            await interaction.response.send_message("❌ Користувач не знайдений на сервері!", ephemeral=True)
            return
        
        # Знаходимо роль
        role = interaction.guild.get_role(self.role_id)
        if not role:
            await interaction.response.send_message("❌ Роль не знайдена!", ephemeral=True)
            return
        
        try:
            await user.add_roles(role, reason=f"Схвалено модератором {interaction.user}")
            
            # Повідомлення в тікеті
            embed = discord.Embed(
                title="✅ Заявку схвалено!",
                description=f"**Користувач:** {user.mention}\n**Роль:** {role.mention}\n**Модератор:** {interaction.user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="🎉 Вітаємо!",
                value=f"Роль **{role.name}** успішно додано до профілю користувача!",
                inline=False
            )
            
            await interaction.response.edit_message(embed=embed, view=TicketCloseView())
            
            # DM користувачу
            try:
                dm_embed = discord.Embed(
                    title="🎉 Заявку схвалено!",
                    description=f"Вашу заявку на роль **{role.name}** схвалено!\n\n" +
                               f"🔹 Сервер: **{interaction.guild.name}**\n" +
                               f"🔹 Роль додано до вашого профілю\n" +
                               f"🔹 Модератор: {interaction.user.mention}",
                    color=discord.Color.green()
                )
                dm_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
                await user.send(embed=dm_embed)
            except:
                # Якщо не може відправити DM - повідомляємо в каналі
                await interaction.followup.send(
                    f"⚠️ {user.mention}, не вдалося відправити повідомлення в ПП. " +
                    f"Ваша заявка схвалена і роль {role.mention} додано!",
                    ephemeral=False
                )
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Помилка додавання ролі: {e}", ephemeral=True)
    
    @discord.ui.button(label="❌ Відхилити заявку", style=discord.ButtonStyle.red, custom_id="reject_role_application")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        # Modal для причини відхилення
        modal = RejectModal(self.role_id, self.user_id)
        await interaction.response.send_modal(modal)

class GeneralTicketButtons(discord.ui.View):
    def __init__(self, ticket_type: str = None, user_id: int = None):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Вирішено", style=discord.ButtonStyle.green, custom_id="resolve_general_ticket")
    async def resolve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        if not self.ticket_type or not self.user_id:
            await interaction.response.send_message("❌ Дані тікета втрачено.", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        config = TICKET_TYPES.get(self.ticket_type, {"name": "Невідомий тип"})
        
        embed = discord.Embed(
            title="✅ Тікет вирішено",
            description=f"**Користувач:** {user.mention if user else 'Користувач покинув сервер'}\n" +
                       f"**Тип тікета:** {config['name']}\n" +
                       f"**Модератор:** {interaction.user.mention}",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="📋 Статус",
            value="Тікет успішно вирішено та готовий до закриття",
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            try:
                dm_embed = discord.Embed(
                    title="✅ Тікет вирішено",
                    description=f"Ваш тікет типу **{config['name']}** було вирішено.\n\n" +
                               f"🔹 Сервер: **{interaction.guild.name}**\n" +
                               f"🔹 Модератор: {interaction.user.mention}\n" +
                               f"🔹 Дякуємо за звернення!",
                    color=discord.Color.green()
                )
                await user.send(embed=dm_embed)
            except:
                pass

class RejectModal(discord.ui.Modal, title="Причина відхилення"):
    def __init__(self, role_id: int, user_id: int):
        super().__init__(timeout=300)
        self.role_id = role_id
        self.user_id = user_id
    
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
        
        embed = discord.Embed(
            title="❌ Заявку відхилено",
            description=f"**Користувач:** {user.mention if user else 'Користувач покинув сервер'}\n" +
                       f"**Роль:** {role.mention if role else 'Роль видалена'}\n" +
                       f"**Модератор:** {interaction.user.mention}",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(
            name="📝 Причина відхилення",
            value=self.reason.value,
            inline=False
        )
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            try:
                dm_embed = discord.Embed(
                    title="❌ Заявку відхилено",
                    description=f"На жаль, вашу заявку на роль **{role.name if role else 'невідома роль'}** відхилено.\n\n" +
                               f"🔹 Сервер: **{interaction.guild.name}**\n" +
                               f"🔹 Причина: {self.reason.value}\n" +
                               f"🔹 Ви можете подати нову заявку пізніше",
                    color=discord.Color.red()
                )
                await user.send(embed=dm_embed)
            except:
                pass

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🔒 Закрити тікет", style=discord.ButtonStyle.secondary, custom_id="close_ticket_final")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Тікет закривається",
            description=f"Тікет закрито модератором {interaction.user.mention}\n\n" +
                       f"📅 Час закриття: <t:{int(datetime.now().timestamp())}:F>\n" +
                       f"⏰ Канал буде видалено через 15 секунд...",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Дякуємо за використання системи тікетів!")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Логування закриття
        await self.log_ticket_closure(interaction)
        
        # Видаляємо канал через 15 секунд
        await asyncio.sleep(15)
        try:
            await interaction.followup.channel.delete(reason=f"Тікет закрито модератором {interaction.user}")
        except:
            pass
    
    async def log_ticket_closure(self, interaction: discord.Interaction):
        """Логування закриття тікета"""
        if not CONFIG["LOG_CHANNEL_ID"]:
            return
        
        log_channel = interaction.guild.get_channel(CONFIG["LOG_CHANNEL_ID"])
        if not log_channel:
            return
        
        try:
            embed = discord.Embed(
                title="🔒 Тікет закрито",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="📍 Канал", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="🛡️ Модератор", value=interaction.user.mention, inline=True)
            embed.add_field(name="⏰ Час закриття", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=True)
            
            await log_channel.send(embed=embed)
        except:
            pass

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
        print("🎫 Persistent views завантажено!")
    
    @app_commands.command(name="ticket", description="🎫 Створити тікет")
    async def create_ticket(self, interaction: discord.Interaction):
        """Головна команда для створення тікетів"""
        
        embed = discord.Embed(
            title="🎫 Система тікетів",
            description="**Ласкаво просимо до системи підтримки!**\n\n" +
                       "Оберіть тип тікета, який найкраще описує вашу ситуацію:",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Додаємо поля з описом кожного типу
        for ticket_type, config in TICKET_TYPES.items():
            embed.add_field(
                name=f"{config['emoji']} {config['name']}",
                value=f"• {config['description']}",
                inline=False
            )
        
        embed.add_field(
            name="📋 Важливо:",
            value="• Один користувач може мати лише один активний тікет кожного типу\n" +
                  "• Будьте чесними та детальними у відповідях\n" +
                  "• Модерація відповість найближчим часом",
            inline=False
        )
        
        embed.set_footer(text="Виберіть опцію з меню нижче ⬇️")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        view = TicketMainView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="ticket_panel", description="🛠️ Створити панель тікетів (тільки адміни)")
    @app_commands.describe(channel="Канал для розміщення панелі тікетів")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Команда для налаштування постійної панелі тікетів"""
        
        # Перевіряємо права
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Тільки адміністратори можуть використовувати цю команду!", ephemeral=True)
            return
        
        target_channel = channel or interaction.channel
        
        # Головний embed
        main_embed = discord.Embed(
            title="🎫 Система тікетів підтримки",
            description=f"**Ласкаво просимо на сервер {interaction.guild.name}!**\n\n" +
                       "Якщо у вас є питання, проблеми або пропозиції - створіть тікет!\n" +
                       "Наша команда модераторів завжди готова допомогти. ✨",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Додаємо інформацію про типи тікетів
        ticket_info = ""
        for ticket_type, config in TICKET_TYPES.items():
            ticket_info += f"{config['emoji']} **{config['name']}**\n├ {config['description']}\n\n"
        
        main_embed.add_field(
            name="📋 Доступні типи тікетів:",
            value=ticket_info.strip(),
            inline=False
        )
        
        main_embed.add_field(
            name="📌 Правила використання:",
            value="🔹 Один активний тікет кожного типу на користувача\n" +
                  "🔹 Відповідайте чесно та детально\n" +
                  "🔹 Будьте ввічливими з модерацією\n" +
                  "🔹 Не створюйте тікети без потреби",
            inline=False
        )
        
        main_embed.add_field(
            name="⏰ Час роботи підтримки:",
            value="Модерація працює цілодобово, але час відповіді може варіюватися від декількох хвилин до декількох годин залежно від складності питання.",
            inline=False
        )
        
        main_embed.set_footer(text="🔹 Натисніть на меню нижче щоб створити тікет")
        main_embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        # Додатковий embed з інструкціями
        instruction_embed = discord.Embed(
            title="📖 Як створити тікет?",
            color=discord.Color.green()
        )
        
        instruction_embed.add_field(
            name="Крок 1️⃣",
            value="Натисніть на меню вибору нижче",
            inline=True
        )
        
        instruction_embed.add_field(
            name="Крок 2️⃣", 
            value="Оберіть тип вашого питання",
            inline=True
        )
        
        instruction_embed.add_field(
            name="Крок 3️⃣",
            value="Дочекайтеся створення приватного каналу",
            inline=True
        )
        
        instruction_embed.add_field(
            name="Крок 4️⃣",
            value="Відповідайте на питання бота",
            inline=True
        )
        
        instruction_embed.add_field(
            name="Крок 5️⃣",
            value="Дочекайтеся відповіді модератора",
            inline=True
        )
        
        instruction_embed.add_field(
            name="Крок 6️⃣",
            value="Дякуємо за звернення! 🎉",
            inline=True
        )
        
        view = TicketMainView()
        
        # Відправляємо повідомлення
        await target_channel.send(embeds=[main_embed, instruction_embed], view=view)
        
        success_embed = discord.Embed(
            title="✅ Панель тікетів створено!",
            description=f"Панель успішно розміщено в {target_channel.mention}\n\n" +
                       f"🔹 Користувачі тепер можуть створювати тікети\n" +
                       f"🔹 Переконайтесь що ID модераторської ролі вказано правильно\n" +
                       f"🔹 За потреби налаштуйте права доступу до категорії",
            color=discord.Color.green()
        )
        
        await interaction.response.send_message(embed=success_embed, ephemeral=True)
    
    @app_commands.command(name="close_ticket", description="🔒 Закрити поточний тікет (тільки модератори)")
    async def close_ticket_command(self, interaction: discord.Interaction):
        """Команда для закриття тікета"""
        
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        # Перевіряємо чи це тікет канал
        if not any(ticket_type in interaction.channel.name for ticket_type in TICKET_TYPES.keys()):
            await interaction.response.send_message("❌ Ця команда працює тільки в каналах тікетів!", ephemeral=True)
            return
        
        # Створюємо embed для підтвердження
        embed = discord.Embed(
            title="⚠️ Підтвердження закриття",
            description=f"Ви впевнені що хочете закрити цей тікет?\n\n" +
                       f"🔹 Канал: {interaction.channel.mention}\n" +
                       f"🔹 Модератор: {interaction.user.mention}\n" +
                       f"🔹 Канал буде видалено **безповоротно**",
            color=discord.Color.orange()
        )
        
        view = ConfirmCloseView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="ticket_config", description="⚙️ Налаштування системи тікетів")
    @app_commands.describe(
        moderator_role="Роль модераторів",
        log_channel="Канал для логів тікетів",
        category="Категорія для тікетів"
    )
    async def config_tickets(
        self, 
        interaction: discord.Interaction,
        moderator_role: discord.Role = None,
        log_channel: discord.TextChannel = None,
        category: discord.CategoryChannel = None
    ):
        """Налаштування конфігурації системи тікетів"""
        
        # Перевіряємо права
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Тільки адміністратори можуть використовувати цю команду!", ephemeral=True)
            return
        
        changes_made = []
        
        if moderator_role:
            CONFIG["MODERATOR_ROLE_ID"] = moderator_role.id
            changes_made.append(f"🛡️ Роль модераторів: {moderator_role.mention}")
        
        if log_channel:
            CONFIG["LOG_CHANNEL_ID"] = log_channel.id
            changes_made.append(f"📝 Канал логів: {log_channel.mention}")
        
        if category:
            CONFIG["CATEGORY_ID"] = category.id
            changes_made.append(f"📁 Категорія тікетів: {category.name}")
        
        if changes_made:
            embed = discord.Embed(
                title="✅ Конфігурацію оновлено!",
                description="**Змінено наступні налаштування:**\n\n" + "\n".join(changes_made),
                color=discord.Color.green()
            )
        else:
            # Показуємо поточну конфігурацію
            mod_role = interaction.guild.get_role(CONFIG["MODERATOR_ROLE_ID"])
            log_ch = interaction.guild.get_channel(CONFIG["LOG_CHANNEL_ID"])
            cat = interaction.guild.get_channel(CONFIG["CATEGORY_ID"])
            
            embed = discord.Embed(
                title="⚙️ Поточна конфігурація",
                color=discord.Color.blue()
            )
            
            embed.add_field(
                name="🛡️ Роль модераторів",
                value=mod_role.mention if mod_role else "❌ Не налаштовано",
                inline=False
            )
            
            embed.add_field(
                name="📝 Канал логів",
                value=log_ch.mention if log_ch else "❌ Не налаштовано",
                inline=False
            )
            
            embed.add_field(
                name="📁 Категорія тікетів",
                value=cat.name if cat else "❌ Буде створена автоматично",
                inline=False
            )
            
            embed.add_field(
                name="📋 Доступні ролі для заявок",
                value=f"{len(CONFIG['AVAILABLE_ROLES'])} ролей" if CONFIG['AVAILABLE_ROLES'] else "Всі ролі сервера",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="ticket_stats", description="📊 Статистика тікетів")
    async def ticket_stats(self, interaction: discord.Interaction):
        """Показує статистику системи тікетів"""
        
        # Підраховуємо активні тікети
        active_tickets = 0
        tickets_by_type = {}
        
        category = None
        if CONFIG["CATEGORY_ID"]:
            category = interaction.guild.get_channel(CONFIG["CATEGORY_ID"])
        
        if category:
            for channel in category.text_channels:
                active_tickets += 1
                # Визначаємо тип тікета з назви каналу
                for ticket_type in TICKET_TYPES.keys():
                    if ticket_type in channel.name:
                        tickets_by_type[ticket_type] = tickets_by_type.get(ticket_type, 0) + 1
                        break
        
        embed = discord.Embed(
            title="📊 Статистика системи тікетів",
            description=f"**Загальна інформація на {datetime.now().strftime('%d.%m.%Y %H:%M')}**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        embed.add_field(
            name="🎫 Активні тікети",
            value=f"**{active_tickets}** тікетів відкрито",
            inline=True
        )
        
        embed.add_field(
            name="📁 Категорія",
            value=category.mention if category else "❌ Не знайдена",
            inline=True
        )
        
        embed.add_field(
            name="🛡️ Модератори",
            value=f"<@&{CONFIG['MODERATOR_ROLE_ID']}>",
            inline=True
        )
        
        # Розбивка по типам тікетів
        if tickets_by_type:
            breakdown = ""
            for ticket_type, count in tickets_by_type.items():
                config = TICKET_TYPES.get(ticket_type, {})
                emoji = config.get('emoji', '❓')
                name = config.get('name', ticket_type)
                breakdown += f"{emoji} {name}: **{count}**\n"
            
            embed.add_field(
                name="📋 Розбивка по типам",
                value=breakdown.strip(),
                inline=False
            )
        
        embed.set_footer(text=f"ID сервера: {interaction.guild.id}")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class ConfirmCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=60)
    
    @discord.ui.button(label="✅ Так, закрити", style=discord.ButtonStyle.danger, custom_id="confirm_close_ticket")
    async def confirm_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🔒 Тікет закривається",
            description=f"Тікет закрито модератором {interaction.user.mention}\n\n" +
                       f"📅 Час закриття: <t:{int(datetime.now().timestamp())}:F>\n" +
                       f"⏰ Канал буде видалено через 10 секунд...",
            color=discord.Color.orange(),
            timestamp=datetime.now()
        )
        embed.set_footer(text="Дякуємо за використання системи тікетів!")
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Логування закриття
        await self.log_ticket_closure(interaction)
        
        # Видаляємо канал через 10 секунд
        await asyncio.sleep(10)
        try:
            await interaction.followup.channel.delete(reason=f"Тікет закрито модератором {interaction.user}")
        except:
            pass
    
    @discord.ui.button(label="❌ Скасувати", style=discord.ButtonStyle.secondary, custom_id="cancel_close_ticket")
    async def cancel_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="✅ Скасовано",
            description="Закриття тікета скасовано.",
            color=discord.Color.green()
        )
        await interaction.response.edit_message(embed=embed, view=None)
    
    async def log_ticket_closure(self, interaction: discord.Interaction):
        """Логування закриття тікета"""
        if not CONFIG["LOG_CHANNEL_ID"]:
            return
        
        log_channel = interaction.guild.get_channel(CONFIG["LOG_CHANNEL_ID"])
        if not log_channel:
            return
        
        try:
            embed = discord.Embed(
                title="🔒 Тікет закрито",
                color=discord.Color.orange(),
                timestamp=datetime.now()
            )
            embed.add_field(name="📍 Канал", value=f"#{interaction.channel.name}", inline=True)
            embed.add_field(name="🛡️ Модератор", value=interaction.user.mention, inline=True)
            embed.add_field(name="⏰ Час закриття", value=f"<t:{int(datetime.now().timestamp())}:F>", inline=False)
            
            await log_channel.send(embed=embed)
        except:
            pass
    
    async def on_timeout(self):
        # Відключаємо кнопки після таймауту
        for item in self.children:
            item.disabled = True

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    print("🎫 Ticket System завантажено!")