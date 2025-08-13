import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database

db = get_database()

class RoomManagementView(discord.ui.View):
    def __init__(self, user_id):
        super().__init__(timeout=None)
        self.user_id = user_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        """Перевіряє чи користувач має право використовувати кнопки"""
        # Тут можна додати перевірку чи користувач має приватний канал
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ Ці кнопки можеш використовувати тільки ти!", ephemeral=True)
            return False
        return True

    @discord.ui.button(emoji="<:pen:1405110194651795466>", style=discord.ButtonStyle.secondary, row=0)
    async def edit_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Змінити назву кімнати"""
        await interaction.response.send_message("✏️ Напиши нову назву для своєї кімнати:", ephemeral=True)
        # Тут буде логіка зміни назви

    @discord.ui.button(emoji="<:members_limit:1405110200708497419>", style=discord.ButtonStyle.secondary, row=0)
    async def set_limit(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Встановити ліміт користувачів"""
        await interaction.response.send_message("👥 Напиши ліміт користувачів (0-99):", ephemeral=True)
        # Тут буде логіка встановлення ліміту

    @discord.ui.button(emoji="<:lock_unlock:1405110188259934298>", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_lock(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Закрити/відкрити доступ"""
        # Тут буде логіка перевірки поточного стану
        await interaction.response.send_message("🔒 Кімнату закрито для нових користувачів!", ephemeral=True)

    @discord.ui.button(emoji="<:eye_closed:1405110183385894932>", style=discord.ButtonStyle.secondary, row=0)
    async def toggle_visibility(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Сховати/показати кімнату"""
        await interaction.response.send_message("👁️ Видимість кімнати змінено!", ephemeral=True)

    @discord.ui.button(emoji="<:plus:1405110182014357595>", style=discord.ButtonStyle.secondary, row=0)
    async def manage_access(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Управління доступом користувачів"""
        await interaction.response.send_message("➕ Згадай користувача якому хочеш дати/заборонити доступ:", ephemeral=True)

    @discord.ui.button(emoji="<:microphone:1405110190239514654>", style=discord.ButtonStyle.secondary, row=1)
    async def manage_mic(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Управління правами мікрофону"""
        await interaction.response.send_message("🎤 Згадай користувача якому хочеш дати/заборонити мікрофон:", ephemeral=True)

    @discord.ui.button(emoji="<:kick_user:1405110186313519226>", style=discord.ButtonStyle.secondary, row=1)
    async def kick_user(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Вигнати користувача"""
        await interaction.response.send_message("➖ Згадай користувача якого хочеш вигнати:", ephemeral=True)

    @discord.ui.button(emoji="<:reset:1405110197248069733>", style=discord.ButtonStyle.secondary, row=1)
    async def reset_permissions(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Скинути права користувача"""
        await interaction.response.send_message("🔄 Згадай користувача якому хочеш скинути права:", ephemeral=True)

    @discord.ui.button(emoji="<:star_owner:1405110192462495744>", style=discord.ButtonStyle.secondary, row=1)
    async def transfer_ownership(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Передати власність"""
        await interaction.response.send_message("⭐ Згадай користувача якому хочеш передати власність кімнати:", ephemeral=True)

    @discord.ui.button(emoji="<:room_info:1405110199127248896>", style=discord.ButtonStyle.primary, row=1)
    async def room_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Інформація про кімнату"""
        # Тут буде логіка отримання інформації про кімнату з БД
        embed = discord.Embed(
            title="📋 Інформація про твою кімнату",
            color=0x7c7cf0,
            description="🏠 **Назва:** Моя приватна кімната\n"
                       "👥 **Ліміт:** 10 користувачів\n"
                       "🔒 **Статус:** Відкрито\n"
                       "👁️ **Видимість:** Видимо всім\n"
                       "👑 **Власник:** <@{}>".format(interaction.user.id)
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

class RoomManagementCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="room", description="Управління своєю приватною кімнатою")
    async def room_management(self, interaction: discord.Interaction):
        """Основна команда для управління приватною кімнатою"""
        await interaction.response.defer(ephemeral=True)

        # Перевірка чи користувач має приватний канал
        # user_channel = await self.get_user_private_channel(interaction.user.id)
        # if not user_channel:
        #     await interaction.followup.send("❌ У тебе немає приватного каналу! Зайди в канал-створювач щоб створити свій.", ephemeral=True)
        #     return

        embed = discord.Embed(
            title="🏠 Управління приватною кімнатою",
            color=0x7c7cf0,
            description=(
                "Натисни наступні кнопочки, щоб налаштувати свою кімнату\n"
                "Використовувати їх можна тільки коли у тебе є приватний канал\n\n"
                "<:pen:1405110194651795466> — змінити назву кімнати\n"
                "<:members_limit:1405110200708497419> — встановити ліміт користувачів\n"
                "<:lock_unlock:1405110188259934298> — закрити/відкрити доступ в кімнату\n"
                "<:eye_closed:1405110183385894932> — сховати/розкрити кімнату для всіх\n"
                "<:plus:1405110182014357595> — заборонити/дати доступ до кімнати користувачеві\n"
                "<:microphone:1405110190239514654> — заборонити/дати право говорити користувачеві\n"
                "<:kick_user:1405110186313519226> — вигнати користувача з кімнати\n"
                "<:reset:1405110197248069733> — скинути права користувача\n"
                "<:star_owner:1405110192462495744> — зробити користувача новим власником\n"
                "<:room_info:1405110199127248896> — інформація про кімнату"
            )
        )
        embed.set_footer(text="Кнопки працюють постійно")

        view = RoomManagementView(interaction.user.id)
        await interaction.followup.send(embed=embed, view=view, ephemeral=True)

    async def get_user_private_channel(self, user_id):
        """Отримати приватний канал користувача з БД"""
        # Приклад запиту до БД
        user_room = await db.private_rooms.find_one({
            "owner_id": user_id,
            "active": True
        })
        return user_room

    async def update_room_setting(self, user_id, setting, value):
        """Оновити налаштування кімнати в БД"""
        await db.private_rooms.update_one(
            {"owner_id": user_id, "active": True},
            {"$set": {setting: value}}
        )

async def setup(bot):
    await bot.add_cog(RoomManagementCommands(bot))