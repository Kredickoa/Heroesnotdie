import discord
from discord import app_commands
from discord.ext import commands, tasks
from modules.db import get_database
from datetime import datetime, timedelta

db = get_database()

class Pulse(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_active_roles.start()

    def cog_unload(self):
        self.check_active_roles.cancel()

    @app_commands.command(name="pulse-setup", description="Налаштувати Pulse систему на сервері")
    @app_commands.describe(
        role="Роль для активних гравців",
        min_level="Мінімальний рівень (за замовчуванням: 5)",
        min_xp_5d="Мінімум XP за 5 днів (за замовчуванням: 500)"
    )
    @app_commands.default_permissions(manage_roles=True)
    async def pulse_setup(self, interaction: discord.Interaction, role: discord.Role, min_level: int = 5, min_xp_5d: int = 500):
        """Налаштувати систему Pulse з ролями та умовами активності"""
        if role.position >= interaction.guild.me.top_role.position:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Роль знаходиться вище за мою найвищу роль! Перемістіть мою роль вище або оберіть іншу роль.",
                color=0xff0000
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        await db.settings.update_one(
            {"guild_id": str(interaction.guild.id)},
            {
                "$set": {
                    "active_role_id": role.id,
                    "min_level": min_level,
                    "min_xp_5d": min_xp_5d,
                    "enabled": True
                }
            },
            upsert=True
        )

        embed = discord.Embed(
            title="✅ Pulse налаштовано!",
            description="Система Pulse успішно налаштована",
            color=0x00ff00
        )
        embed.add_field(name="Роль:", value=role.mention, inline=True)
        embed.add_field(name="Мін. рівень:", value=str(min_level), inline=True)
        embed.add_field(name="Мін. XP за 5 днів:", value=str(min_xp_5d), inline=True)
        embed.add_field(
            name="ℹ️ Інформація:",
            value="Перевірка активності відбувається автоматично кожні 24 години.",
            inline=False
        )
        
        await interaction.response.send_message(embed=embed)

        # Перевірка та видача ролі одразу після налаштування для автора команди
        member = interaction.user
        added, removed = await self._check_member_active_role(member, interaction.guild)
        if added > 0:
            await interaction.followup.send(f"✅ Роль {role.mention} видана вам, оскільки ви відповідаєте умовам!", ephemeral=True)

    @app_commands.command(name="pulse-status", description="Показати поточні налаштування Pulse")
    @app_commands.default_permissions(manage_roles=True)
    async def pulse_status(self, interaction: discord.Interaction):
        setting = await db.settings.find_one({"guild_id": str(interaction.guild.id)})
        
        if not setting or "active_role_id" not in setting:
            embed = discord.Embed(
                title="ℹ️ Статус Pulse",
                description="Система не налаштована на цьому сервері",
                color=0xffaa00
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        role = interaction.guild.get_role(setting["active_role_id"])
        if not role:
            embed = discord.Embed(
                title="⚠️ Помилка",
                description="Налаштована роль була видалена",
                color=0xff0000
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="📊 Статус Pulse",
            description="Поточні налаштування системи:",
            color=0x0099ff
        )
        embed.add_field(name="Роль:", value=role.mention, inline=True)
        embed.add_field(name="Мін. рівень:", value=str(setting.get("min_level", 5)), inline=True)
        embed.add_field(name="Мін. XP за 5 днів:", value=str(setting.get("min_xp_5d", 500)), inline=True)
        embed.add_field(name="Учасників з роллю:", value=str(len(role.members)), inline=True)
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pulse-disable", description="Вимкнути Pulse систему на сервері")
    @app_commands.default_permissions(manage_roles=True)
    async def pulse_disable(self, interaction: discord.Interaction):
        result = await db.settings.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$unset": {"active_role_id": "", "min_level": "", "min_xp_5d": "", "enabled": ""}}
        )
        
        if result.modified_count > 0:
            embed = discord.Embed(
                title="✅ Систему вимкнено",
                description="Pulse систему було успішно вимкнено",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Інформація",
                description="Pulse система не була налаштована на цьому сервері",
                color=0xffaa00
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="pulse-check", description="Ручна перевірка активності всіх користувачів")
    @app_commands.default_permissions(manage_roles=True)
    async def pulse_check(self, interaction: discord.Interaction):
        setting = await db.settings.find_one({"guild_id": str(interaction.guild.id)})
        
        if not setting or "active_role_id" not in setting:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Pulse система не налаштована на цьому сервері",
                color=0xff0000
            )
            return await interaction.response.send_message(embed=embed, ephemeral=True)

        embed = discord.Embed(
            title="🔄 Перевірка активності",
            description="Починаю перевірку активності всіх користувачів...",
            color=0xffaa00
        )
        await interaction.response.send_message(embed=embed)

        added, removed = await self._check_guild_active_roles(interaction.guild, setting)

        embed = discord.Embed(
            title="✅ Перевірку завершено",
            description="Результати ручної перевірки активності:",
            color=0x00ff00
        )
        embed.add_field(name="Додано ролей:", value=str(added), inline=True)
        embed.add_field(name="Знято ролей:", value=str(removed), inline=True)
        
        await interaction.edit_original_response(embed=embed)

  async def _check_member_active_role(self, member, guild):
    setting = await db.settings.find_one({"guild_id": str(guild.id)})
    if not setting or "active_role_id" not in setting:
        return 0, 0

    role = guild.get_role(setting["active_role_id"])
    if not role:
        return 0, 0

    min_level = setting.get("min_level", 5)
    min_xp_5d = setting.get("min_xp_5d", 100)
    cutoff_date = datetime.utcnow() - timedelta(days=5)

    user_data = await db.users.find_one({"guild_id": str(guild.id), "user_id": str(member.id)})
    if not user_data:
        if role in member.roles:
            try:
                await member.remove_roles(role, reason="Inactive (no profile)")
                return 0, 1
            except Exception:
                return 0, 0
        return 0, 0

    level = user_data.get("level", 0)
    history = user_data.get("history", {})
    recent_xp = sum(history.get((datetime.utcnow().date() - timedelta(days=i)).strftime("%Y-%m-%d"), 0) for i in range(5))
    print(f"Checking {member.name}, level: {level}, xp: {recent_xp}")

    has_role = role in member.roles
    added = 0
    removed = 0

    if level >= min_level and recent_xp >= min_xp_5d:
        if not has_role:
            try:
                await member.add_roles(role, reason="Active player role assigned")
                added = 1
            except Exception as e:
                print(f"Error adding role to {member.name}: {e}")
    else:
        if has_role:
            try:
                await member.remove_roles(role, reason="Active player role removed (inactive)")
                removed = 1
            except Exception as e:
                print(f"Error removing role from {member.name}: {e}")

    return added, removed

    async def _check_guild_active_roles(self, guild, setting):
        role_id = setting["active_role_id"]
        min_level = setting.get("min_level", 5)
        min_xp_5d = setting.get("min_xp_5d", 500)

        role = guild.get_role(role_id)
        if not role:
            return 0, 0

        cutoff_date = datetime.utcnow() - timedelta(days=5)
        added_count = 0
        removed_count = 0

        for member in guild.members:
            if member.bot:
                continue

            added, removed = await self._check_member_active_role(member, guild)
            added_count += added
            removed_count += removed

        return added_count, removed_count

    @tasks.loop(hours=24)
    async def check_active_roles(self):
        async for setting in db.settings.find({"active_role_id": {"$exists": True}}):
            guild_id = int(setting["guild_id"])
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue

            try:
                await self._check_guild_active_roles(guild, setting)
            except Exception as e:
                print(f"Error checking active roles for guild {guild_id}: {e}")

    @check_active_roles.before_loop
    async def before_check(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Pulse(bot))