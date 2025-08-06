import discord
from discord import app_commands
from discord.ext import commands
from discord import Embed, Colour
from modules.db import get_database  # Імпорт функції get_database з modules/db.py

class RoleForLevelCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = get_database()  # Ініціалізуємо базу даних

    @app_commands.command(name="setroleforlevel", description="Налаштувати роль для користувачів із певним рівнем")
    @app_commands.default_permissions(manage_roles=True)  # Тільки для адміністраторів
    @app_commands.describe(
        role="Роль, яку потрібно присвоїти користувачам",
        level="Мінімальний рівень для отримання ролі (наприклад, 5)"
    )
    async def setroleforlevel(self, interaction: discord.Interaction, role: discord.Role, level: int):
        await interaction.response.defer(ephemeral=True)  # Відкладаємо відповідь

        # Перевірка підключення до бази даних
        if not self.db:
            await interaction.followup.send("Помилка: не вдалося підключитися до бази даних!", ephemeral=True)
            return

        guild = interaction.guild
        # Перевірка, чи бот має права керувати ролями
        if not guild.me.guild_permissions.manage_roles:
            await interaction.followup.send("У мене немає дозволу на керування ролями!", ephemeral=True)
            return

        # Перевірка, чи роль бота вища за вказану роль у ієрархії
        if role.position >= guild.me.top_role.position:
            await interaction.followup.send("Я не можу присвоювати цю роль, оскільки вона вища за мою в ієрархії!", ephemeral=True)
            return

        try:
            # Отримуємо дані лідерборду з колекції users
            leaderboard = self.db.users.find({"guild_id": str(guild.id)})
            eligible_users = [user for user in leaderboard if user.get("level", 0) >= level]

            # Присвоюємо роль відповідним користувачам
            assigned_count = 0
            for user_data in eligible_users:
                member = guild.get_member(int(user_data["user_id"]))
                if member and role not in member.roles:
                    await member.add_roles(role)
                    assigned_count += 1

            # Зберігаємо налаштування ролі та рівня в колекції role_assignments
            self.db.role_assignments.update_one(
                {"guild_id": str(guild.id)},
                {"$set": {"role_id": str(role.id), "required_level": level}},
                upsert=True
            )

            # Створюємо гарний ембед
            embed = Embed(
                title="Налаштування ролі для рівня",
                description=(
                    f"Роль {role.mention} успішно призначена для користувачів із рівнем **{level}** і вище.\n"
                    f"Кількість користувачів, яким присвоєно роль: **{assigned_count}**."
                ),
                colour=Colour.green(),
                timestamp=discord.utils.utcnow()
            )
            embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
            embed.set_footer(text=f"Налаштував: {interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)

            # Надсилаємо ембед
            await interaction.followup.send(embed=embed, ephemeral=False)

        except Exception as e:
            await interaction.followup.send(f"Сталася помилка: {str(e)}", ephemeral=True)
            print(f"[ERROR] Помилка в команді setroleforlevel: {e}")

async def setup(bot):
    await bot.add_cog(RoleForLevelCommand(bot))