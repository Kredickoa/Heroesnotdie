import discord
from discord.ext import commands
from discord import app_commands
import json
import asyncio

# Глобальне сховище для даних кнопок
button_data = {}

class AnnouncementView(discord.ui.View):
    def __init__(self, message_id: str):
        super().__init__(timeout=None)
        self.message_id = message_id
    
    @discord.ui.button(label="Кнопка", style=discord.ButtonStyle.secondary, custom_id="placeholder")
    async def placeholder_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Цей метод буде перевизначений динамічно
        pass

class AnnouncementCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.button_data = {}

    @app_commands.command(name="setup-announcement", description="Створити оголошення з кнопками")
    @app_commands.describe(
        title="Заголовок оголошення",
        description="Текст оголошення",
        color="Колір embed (hex код, наприклад FF1493)",
        button1_text="Текст першої кнопки",
        button1_content="Контент першої кнопки (текст або link:посилання)",
        button2_text="Текст другої кнопки",
        button2_content="Контент другої кнопки (текст або link:посилання)",
        button3_text="Текст третьої кнопки",
        button3_content="Контент третьої кнопки (текст або link:посилання)",
        button4_text="Текст четвертої кнопки",
        button4_content="Контент четвертої кнопки (текст або link:посилання)",
        channel="Канал для відправки"
    )
    @app_commands.default_permissions(administrator=True)
    async def setup_announcement(
        self,
        interaction: discord.Interaction,
        title: str,
        description: str = None,
        color: str = "FF1493",
        button1_text: str = None,
        button1_content: str = None,
        button2_text: str = None,
        button2_content: str = None,
        button3_text: str = None,
        button3_content: str = None,
        button4_text: str = None,
        button4_content: str = None,
        channel: discord.TextChannel = None
    ):
        target_channel = channel or interaction.channel
        
        # Створення embed
        try:
            embed_color = int(color.replace('#', ''), 16)
        except ValueError:
            embed_color = 0xFF1493
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=embed_color,
            timestamp=discord.utils.utcnow()
        )
        
        # Створення view з кнопками
        view = discord.ui.View(timeout=None)
        message_buttons = {}
        
        buttons_data = [
            (button1_text, button1_content),
            (button2_text, button2_content),
            (button3_text, button3_content),
            (button4_text, button4_content)
        ]
        
        button_count = 0
        for i, (btn_text, btn_content) in enumerate(buttons_data, 1):
            if btn_text:
                custom_id = f"custom_button_{i}_{interaction.guild.id}"
                
                if btn_content and btn_content.startswith('link:'):
                    # Кнопка-посилання
                    link = btn_content.replace('link:', '')
                    try:
                        button = discord.ui.Button(
                            label=btn_text,
                            style=discord.ButtonStyle.link,
                            url=link
                        )
                        view.add_item(button)
                        button_count += 1
                    except:
                        continue
                else:
                    # Звичайна кнопка
                    button = discord.ui.Button(
                        label=btn_text,
                        style=discord.ButtonStyle.secondary,
                        custom_id=custom_id
                    )
                    view.add_item(button)
                    message_buttons[custom_id] = {
                        'text': btn_text,
                        'content': btn_content or f"Контент для кнопки \"{btn_text}\" не налаштовано"
                    }
                    button_count += 1
        
        try:
            message = await target_channel.send(embed=embed, view=view if button_count > 0 else None)
            
            # Збереження даних кнопок
            if message_buttons:
                self.button_data[str(message.id)] = message_buttons
            
            await interaction.response.send_message(
                f"✅ Оголошення успішно відправлено в {target_channel.mention}!",
                ephemeral=True
            )
            
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Помилка при відправці оголошення: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="add-button", description="Додати кнопку до існуючого повідомлення")
    @app_commands.describe(
        message_id="ID повідомлення для додавання кнопки",
        button_text="Текст кнопки",
        button_content="Контент кнопки (текст або link:посилання)"
    )
    @app_commands.default_permissions(administrator=True)
    async def add_button(
        self,
        interaction: discord.Interaction,
        message_id: str,
        button_text: str,
        button_content: str
    ):
        try:
            message = await interaction.channel.fetch_message(int(message_id))
        except:
            await interaction.response.send_message(
                "❌ Повідомлення не знайдено в цьому каналі.",
                ephemeral=True
            )
            return
        
        # Створення нової кнопки
        view = discord.ui.View.from_message(message) if message.components else discord.ui.View(timeout=None)
        
        # Перевірка ліміту кнопок
        if len(view.children) >= 5:
            await interaction.response.send_message(
                "❌ Досягнуто максимальну кількість кнопок (5) для одного повідомлення.",
                ephemeral=True
            )
            return
        
        custom_id = f"custom_button_{len(view.children)+1}_{interaction.guild.id}_{message.id}"
        
        if button_content.startswith('link:'):
            # Кнопка-посилання
            link = button_content.replace('link:', '')
            try:
                button = discord.ui.Button(
                    label=button_text,
                    style=discord.ButtonStyle.link,
                    url=link
                )
                view.add_item(button)
            except:
                await interaction.response.send_message(
                    "❌ Некоректне посилання.",
                    ephemeral=True
                )
                return
        else:
            # Звичайна кнопка
            button = discord.ui.Button(
                label=button_text,
                style=discord.ButtonStyle.secondary,
                custom_id=custom_id
            )
            view.add_item(button)
            
            # Збереження даних кнопки
            if str(message.id) not in self.button_data:
                self.button_data[str(message.id)] = {}
            
            self.button_data[str(message.id)][custom_id] = {
                'text': button_text,
                'content': button_content
            }
        
        try:
            await message.edit(view=view)
            await interaction.response.send_message(
                f"✅ Кнопку \"{button_text}\" успішно додано до повідомлення!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Помилка при додаванні кнопки: {str(e)}",
                ephemeral=True
            )

    @app_commands.command(name="edit-announcement", description="Редагувати текст існуючого оголошення")
    @app_commands.describe(
        message_id="ID повідомлення для редагування",
        new_title="Новий заголовок",
        new_description="Новий опис",
        new_color="Новий колір (hex код)"
    )
    @app_commands.default_permissions(administrator=True)
    async def edit_announcement(
        self,
        interaction: discord.Interaction,
        message_id: str,
        new_title: str = None,
        new_description: str = None,
        new_color: str = None
    ):
        try:
            message = await interaction.channel.fetch_message(int(message_id))
        except:
            await interaction.response.send_message(
                "❌ Повідомлення не знайдено в цьому каналі.",
                ephemeral=True
            )
            return
        
        if not message.embeds:
            await interaction.response.send_message(
                "❌ Повідомлення не містить embed.",
                ephemeral=True
            )
            return
        
        # Оновлення embed
        embed = message.embeds[0]
        new_embed = discord.Embed(
            title=new_title if new_title else embed.title,
            description=new_description if new_description is not None else embed.description,
            color=int(new_color.replace('#', ''), 16) if new_color else embed.color,
            timestamp=discord.utils.utcnow()
        )
        
        try:
            await message.edit(embed=new_embed)
            await interaction.response.send_message(
                "✅ Оголошення успішно оновлено!",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(
                f"❌ Помилка при редагуванні: {str(e)}",
                ephemeral=True
            )

    @commands.Cog.listener()
    async def on_interaction(self, interaction: discord.Interaction):
        if interaction.type != discord.InteractionType.component:
            return
        
        custom_id = interaction.data.get('custom_id', '')
        if not custom_id.startswith('custom_button_'):
            return
        
        message_id = str(interaction.message.id)
        
        # Перевірка даних кнопки
        if message_id not in self.button_data or custom_id not in self.button_data[message_id]:
            await interaction.response.send_message(
                "❌ Дані кнопки не знайдено.",
                ephemeral=True
            )
            return
        
        button_info = self.button_data[message_id][custom_id]
        
        # Створення embed з відповіддю
        embed = discord.Embed(
            title=f"📄 {button_info['text']}",
            description=button_info['content'],
            color=0xFF1493,
            timestamp=discord.utils.utcnow()
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AnnouncementCommands(bot))

"""
ПІДСУМОК - ЩО ВМІЄ ЦЕЙ КОД (Python версія):

📋 КОМАНДИ:
1. /setup-announcement - Створює оголошення з embed та до 4 кнопок
2. /add-button - Додає нову кнопку до існуючого повідомлення
3. /edit-announcement - Редагує заголовок, опис та колір існуючого оголошення

🔘 ТИПИ КНОПОК:
- Текстові кнопки (показують контент в embed при натисканні)
- Кнопки-посилання (відкривають зовнішні посилання)

⚙️ ФУНКЦІЇ:
- Налаштування кольору embed
- Динамічне додавання кнопок до існуючих повідомлень
- Редагування тексту без втрати кнопок
- Зберігання даних кнопок в пам'яті бота
- Приватні відповіді на кнопки (ephemeral)
- Перевірка прав адміністратора

💡 ВИКОРИСТАННЯ:
/setup-announcement title:"Новини сервера" description:"Важлива інформація" button1_text:"Правила" button1_content:"Текст правил..." button2_text:"Discord" button2_content:"link:https://discord.gg/example"
"""