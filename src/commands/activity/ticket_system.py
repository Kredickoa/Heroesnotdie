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
    "CATEGORY_ID": 123456789012345678,        # ID категорії для тікетів
    "LOG_CHANNEL_ID": 123456789012345678,     # ID каналу логів (опціонально)
}

# Типи тікетів
TICKET_TYPES = {
    "role_application": {
        "name": "🎭 Заявка на роль",
        "emoji": "🎭",
        "description": "Подати заявку на отримання ролі",
        "roles": {
            "designer": {
                "name": "🎨 Designer",
                "role_id": 123456789012345678,
                "questions": [
                    "Покажіть приклади своїх робіт (посилання на портфоліо):",
                    "Скільки років досвіду у дизайні?",
                    "Які програми використовуєте?",
                    "Чому хочете отримати цю роль?"
                ]
            },
            "developer": {
                "name": "💻 Developer", 
                "role_id": 123456789012345678,
                "questions": [
                    "Які мови програмування знаєте?",
                    "Покажіть приклади коду або проектів:",
                    "Скільки років досвіду в програмуванні?",
                    "Чому хочете отримати цю роль?"
                ]
            },
            "moderator": {
                "name": "🛡️ Moderator",
                "role_id": 123456789012345678,
                "questions": [
                    "Чому хочете стати модератором?",
                    "Як будете вирішувати конфлікти?",
                    "Скільки часу готові приділяти модерації?",
                    "Ваш досвід у модерації?"
                ]
            }
        }
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
            placeholder="Оберіть тип тікета...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="ticket_type_select_main"
        )
    
    async def callback(self, interaction: discord.Interaction):
        ticket_type = self.values[0]
        
        if ticket_type == "role_application":
            # Якщо це заявка на роль - показуємо вибір ролей
            view = RoleSelectView()
            embed = discord.Embed(
                title="🎭 Заявка на роль",
                description="Оберіть роль, на яку хочете подати заявку:",
                color=discord.Color.blue()
            )
            await interaction.response.edit_message(embed=embed, view=view)
        else:
            # Для інших типів - відразу створюємо тікет
            await self.create_ticket(interaction, ticket_type)
    
    async def create_ticket(self, interaction: discord.Interaction, ticket_type: str, role_key: str = None):
        config = TICKET_TYPES[ticket_type]
        
        # Назва тікета
        if role_key:
            ticket_name = f"{config['roles'][role_key]['name']}-{interaction.user.display_name}"
            questions = config['roles'][role_key]['questions']
        else:
            ticket_name = f"{config['name']}-{interaction.user.display_name}"
            questions = config['questions']
        
        # Створюємо приватний канал
        category = interaction.guild.get_channel(CONFIG["CATEGORY_ID"])
        if not category:
            await interaction.response.send_message("❌ Категорія для тікетів не знайдена!", ephemeral=True)
            return
        
        # Права доступу
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            interaction.guild.get_role(CONFIG["MODERATOR_ROLE_ID"]): discord.PermissionOverwrite(
                read_messages=True, send_messages=True, manage_messages=True
            )
        }
        
        try:
            channel = await category.create_text_channel(
                name=ticket_name.lower().replace(" ", "-"),
                overwrites=overwrites
            )
            
            # Embed з інформацією
            embed = discord.Embed(
                title=f"{config['emoji']} {config['name']}",
                description=f"Тікет створено для {interaction.user.mention}",
                color=discord.Color.green(),
                timestamp=datetime.now()
            )
            embed.add_field(
                name="📝 Інструкція",
                value="Модератор поставить вам питання. Відповідайте чесно та детально.",
                inline=False
            )
            embed.set_footer(text=f"ID: {interaction.user.id}")
            
            # Створюємо view з кнопками для модерації
            if ticket_type == "role_application":
                view = RoleApplicationButtons(role_key, interaction.user.id)
            else:
                view = GeneralTicketButtons(ticket_type, interaction.user.id)
            
            message = await channel.send(
                f"👋 {interaction.user.mention} | 🛡️ <@&{CONFIG['MODERATOR_ROLE_ID']}>",
                embed=embed,
                view=view
            )
            
            # Починаємо задавати питання
            await self.ask_questions(channel, questions, interaction.user)
            
            # Відповідь користувачу
            success_embed = discord.Embed(
                title="✅ Тікет створено!",
                description=f"Ваш тікет створено в {channel.mention}\nМодерація незабаром з вами зв'яжется.",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=success_embed, view=None)
            
        except Exception as e:
            await interaction.response.send_message(f"❌ Помилка створення тікета: {e}", ephemeral=True)
    
    async def ask_questions(self, channel: discord.TextChannel, questions: list, user: discord.Member):
        """Задає питання користувачу"""
        await asyncio.sleep(2)  # Невелика затримка
        
        for i, question in enumerate(questions, 1):
            embed = discord.Embed(
                title=f"❓ Питання {i}/{len(questions)}",
                description=question,
                color=discord.Color.blue()
            )
            await channel.send(embed=embed)

class RoleSelect(discord.ui.Select):
    def __init__(self):
        options = []
        roles_config = TICKET_TYPES["role_application"]["roles"]
        
        for role_key, role_config in roles_config.items():
            options.append(
                discord.SelectOption(
                    label=role_config["name"],
                    description=f"Подати заявку на роль {role_config['name']}",
                    value=role_key
                )
            )
        
        super().__init__(
            placeholder="Оберіть роль...",
            options=options,
            min_values=1,
            max_values=1,
            custom_id="role_select_main"
        )
    
    async def callback(self, interaction: discord.Interaction):
        role_key = self.values[0]
        
        # Перевіряємо чи вже має роль
        role_id = TICKET_TYPES["role_application"]["roles"][role_key]["role_id"]
        role = interaction.guild.get_role(role_id)
        
        if role and role in interaction.user.roles:
            await interaction.response.send_message(
                "❌ У вас вже є ця роль!", 
                ephemeral=True
            )
            return
        
        # Створюємо тікет для заявки на роль
        ticket_select = TicketTypeSelect()
        await ticket_select.create_ticket(interaction, "role_application", role_key)

class TicketMainView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(TicketTypeSelect())

class RoleSelectView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())

class RoleApplicationButtons(discord.ui.View):
    def __init__(self, role_key: str = None, user_id: int = None):
        super().__init__(timeout=None)
        self.role_key = role_key
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Схвалити", style=discord.ButtonStyle.green, custom_id="approve_role_btn")
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        # Якщо немає збережених даних - запитуємо у модератора
        if not self.role_key or not self.user_id:
            await interaction.response.send_message("❌ Дані тікета втрачено. Закрийте канал та створіть новий.", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        if not user:
            await interaction.response.send_message("❌ Користувач не знайдений!", ephemeral=True)
            return
        
        # Додаємо роль
        role_config = TICKET_TYPES["role_application"]["roles"][self.role_key]
        role = interaction.guild.get_role(role_config["role_id"])
        
        if role:
            try:
                await user.add_roles(role)
                
                # Повідомлення в тікеті
                embed = discord.Embed(
                    title="✅ Заявку схвалено!",
                    description=f"Роль {role.mention} додано користувачу {user.mention}",
                    color=discord.Color.green(),
                    timestamp=datetime.now()
                )
                embed.add_field(name="Модератор", value=interaction.user.mention)
                
                await interaction.response.edit_message(embed=embed, view=TicketCloseView())
                
                # DM користувачу
                try:
                    dm_embed = discord.Embed(
                        title="🎉 Вітаємо!",
                        description=f"Вашу заявку на роль **{role_config['name']}** схвалено!\nРоль додано до вашого профілю.",
                        color=discord.Color.green()
                    )
                    await user.send(embed=dm_embed)
                except:
                    pass  # Якщо не може відправити DM
                
            except Exception as e:
                await interaction.response.send_message(f"❌ Помилка додавання ролі: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Роль не знайдена!", ephemeral=True)
    
    @discord.ui.button(label="❌ Відхилити", style=discord.ButtonStyle.red, custom_id="reject_role_btn")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        # Якщо немає збережених даних - запитуємо у модератора
        if not self.role_key or not self.user_id:
            await interaction.response.send_message("❌ Дані тікета втрачено. Закрийте канал та створіть новий.", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        role_config = TICKET_TYPES["role_application"]["roles"][self.role_key]
        
        # Повідомлення в тікеті
        embed = discord.Embed(
            title="❌ Заявку відхилено",
            description=f"Заявка користувача {user.mention if user else 'Невідомий'} на роль **{role_config['name']}** відхилена.",
            color=discord.Color.red(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Модератор", value=interaction.user.mention)
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            try:
                dm_embed = discord.Embed(
                    title="❌ Заявку відхилено",
                    description=f"На жаль, вашу заявку на роль **{role_config['name']}** відхилено.\nВи можете подати нову заявку пізніше.",
                    color=discord.Color.red()
                )
                await user.send(embed=dm_embed)
            except:
                pass

class GeneralTicketButtons(discord.ui.View):
    def __init__(self, ticket_type: str = None, user_id: int = None):
        super().__init__(timeout=None)
        self.ticket_type = ticket_type
        self.user_id = user_id
    
    @discord.ui.button(label="✅ Вирішено", style=discord.ButtonStyle.green, custom_id="resolve_ticket_btn")
    async def resolve(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        # Якщо немає збережених даних
        if not self.ticket_type or not self.user_id:
            await interaction.response.send_message("❌ Дані тікета втрачено. Закрийте канал та створіть новий.", ephemeral=True)
            return
        
        user = interaction.guild.get_member(self.user_id)
        config = TICKET_TYPES[self.ticket_type]
        
        embed = discord.Embed(
            title="✅ Тікет вирішено",
            description=f"Тікет користувача {user.mention if user else 'Невідомий'} типу **{config['name']}** вирішено.",
            color=discord.Color.green(),
            timestamp=datetime.now()
        )
        embed.add_field(name="Модератор", value=interaction.user.mention)
        
        await interaction.response.edit_message(embed=embed, view=TicketCloseView())
        
        # DM користувачу
        if user:
            try:
                dm_embed = discord.Embed(
                    title="✅ Тікет вирішено",
                    description=f"Ваш тікет типу **{config['name']}** було вирішено.\nДякуємо за звернення!",
                    color=discord.Color.green()
                )
                await user.send(embed=dm_embed)
            except:
                pass

class TicketCloseView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
    
    @discord.ui.button(label="🔒 Закрити тікет", style=discord.ButtonStyle.secondary, custom_id="close_ticket_btn")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перевіряємо права
        if not any(role.id == CONFIG["MODERATOR_ROLE_ID"] for role in interaction.user.roles):
            await interaction.response.send_message("❌ Недостатньо прав!", ephemeral=True)
            return
        
        embed = discord.Embed(
            title="🔒 Тікет закрито",
            description="Цей тікет буде видалено через 10 секунд.",
            color=discord.Color.orange()
        )
        
        await interaction.response.edit_message(embed=embed, view=None)
        
        # Видаляємо канал через 10 секунд
        await asyncio.sleep(10)
        try:
            await interaction.followup.channel.delete()
        except:
            pass

class TicketSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def cog_load(self):
        """Викликається при завантаженні cog"""
        # Відновлюємо persistent views
        self.bot.add_view(TicketMainView())
        self.bot.add_view(RoleSelectView())
        self.bot.add_view(TicketCloseView())
        self.bot.add_view(RoleApplicationButtons())
        self.bot.add_view(GeneralTicketButtons())
        print("🎫 Persistent views loaded!")
    
    @app_commands.command(name="ticket", description="Створити тікет")
    async def create_ticket(self, interaction: discord.Interaction):
        """Головна команда для створення тікетів"""
        
        embed = discord.Embed(
            title="🎫 Система тікетів",
            description="Оберіть тип тікета, який хочете створити:",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Додаємо поля з описом кожного типу
        for ticket_type, config in TICKET_TYPES.items():
            embed.add_field(
                name=f"{config['emoji']} {config['name']}",
                value=config['description'],
                inline=False
            )
        
        embed.set_footer(text="Виберіть опцію з меню нижче")
        
        view = TicketMainView()
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
    
    @app_commands.command(name="ticket_setup", description="Налаштування системи тікетів (тільки адміни)")
    @app_commands.describe(channel="Канал для розміщення панелі тікетів")
    async def setup_tickets(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        """Команда для налаштування постійної панелі тікетів"""
        
        # Перевіряємо права
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ Тільки адміністратори можуть використовувати цю команду!", ephemeral=True)
            return
        
        target_channel = channel or interaction.channel
        
        embed = discord.Embed(
            title="🎫 Система тікетів",
            description="**Натисніть на меню нижче, щоб створити тікет**\n\n" +
                       "**Доступні типи тікетів:**",
            color=discord.Color.blue(),
            timestamp=datetime.now()
        )
        
        # Додаємо поля з описом кожного типу
        for ticket_type, config in TICKET_TYPES.items():
            if ticket_type == "role_application":
                roles_list = "\n".join([f"• {role_config['name']}" for role_config in config['roles'].values()])
                embed.add_field(
                    name=f"{config['emoji']} {config['name']}",
                    value=f"{config['description']}\n**Доступні ролі:**\n{roles_list}",
                    inline=False
                )
            else:
                embed.add_field(
                    name=f"{config['emoji']} {config['name']}",
                    value=config['description'],
                    inline=False
                )
        
        embed.set_footer(text="🔹 Всі тікети створюються як приватні канали")
        
        view = TicketMainView()
        await target_channel.send(embed=embed, view=view)
        
        await interaction.response.send_message(f"✅ Панель тікетів створено в {target_channel.mention}!", ephemeral=True)

async def setup(bot):
    await bot.add_cog(TicketSystem(bot))
    print("🎫 Ticket System loaded!")