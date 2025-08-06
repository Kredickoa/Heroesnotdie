import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database

class RoleForLevelCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="setroleforlevel", description="Налаштувати роль для користувачів із певним рівнем")
    @app_commands.default_permissions(manage_roles=True)
    @app_commands.describe(
        role="Роль, яку потрібно присвоїти користувачам",
        level="Мінімальний рівень для отримання ролі (наприклад, 5)",
        custom_message="Власне повідомлення (опціонально)",
        emoji="Емодзі для повідомлення (опціонально, за замовчуванням 📊)"
    )
    async def setroleforlevel(self, interaction: discord.Interaction, role: discord.Role, level: int, custom_message: str = None, emoji: str = "📊"):
        await interaction.response.defer(ephemeral=False)

        # Отримуємо базу даних
        db = get_database()
        if db is None:
            await interaction.followup.send("Помилка: не вдалося підключитися до бази даних!")
            return

        guild = interaction.guild
        # Перевірка, чи бот має права керувати ролями
        if not guild.me.guild_permissions.manage_roles:
            await interaction.followup.send("У мене немає дозволу на керування ролями!")
            return

        # Перевірка, чи роль бота вища за вказану роль у ієрархії
        if role.position >= guild.me.top_role.position:
            await interaction.followup.send("Я не можу присвоювати цю роль, оскільки вона вища за мою в ієрархії!")
            return

        try:
            # Спробуємо знайти користувачів з guild_id як рядком і як числом
            users_str = await db.users.find({"guild_id": str(guild.id)}).to_list(1000)
            users_int = await db.users.find({"guild_id": guild.id}).to_list(1000)
            
            # Використовуємо той варіант, де є користувачі
            users = users_str if len(users_str) > 0 else users_int
            eligible_users = [user for user in users if user.get("level", 0) >= level]

            # Присвоюємо роль відповідним користувачам
            assigned_count = 0
            for user_data in eligible_users:
                # Конвертуємо user_id в int, якщо він зберігається як число
                user_id = user_data.get("user_id")
                if isinstance(user_id, str):
                    user_id = int(user_id)
                
                member = guild.get_member(user_id)
                if member and role not in member.roles:
                    await member.add_roles(role)
                    assigned_count += 1

            # Зберігаємо налаштування ролі та рівня в колекції role_assignments
            await db.role_assignments.update_one(
                {"guild_id": str(guild.id)},
                {"$set": {"role_id": str(role.id), "required_level": level}},
                upsert=True
            )

            # Формуємо текстовий результат
            if custom_message:
                # Якщо є власне повідомлення, використовуємо його
                result_lines = [f"{emoji} {custom_message.upper()}"]
                result_lines.append(f"Роль {role.mention} призначена для користувачів із рівнем **{level}** і вище.")
                result_lines.append(f"Кількість користувачів, яким присвоєно роль: **{assigned_count}**.")
                result_lines.append(f"Налаштував: {interaction.user.display_name}")
            else:
                # Стандартне повідомлення
                result_lines = [f"{emoji} НАЛАШТУВАННЯ РОЛІ ДЛЯ РІВНЯ"]
                result_lines.append(f"Роль {role.mention} призначена для користувачів із рівнем **{level}** і вище.")
                result_lines.append(f"Кількість користувачів, яким присвоєно роль: **{assigned_count}**.")
                result_lines.append(f"Налаштував: {interaction.user.display_name}")

            result = "\n".join(result_lines)
            await interaction.followup.send(result)

        except Exception as e:
            await interaction.followup.send(f"Сталася помилка: {str(e)}")

async def setup(bot):
    await bot.add_cog(RoleForLevelCommand(bot))