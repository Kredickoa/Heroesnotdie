import discord
from discord.ext import commands, tasks
from modules.db import get_database
from datetime import datetime, timedelta

db = get_database()

class ActivePingChecker(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.check_active_roles.start()

    def cog_unload(self):
        self.check_active_roles.cancel()

    @discord.app_commands.command(name="activeping-setup", description="Налаштувати систему активних ролей")
    @discord.app_commands.describe(
        role="Роль для активних гравців",
        min_level="Мінімальний рівень (за замовчуванням: 5)",
        min_xp_5d="Мінімум XP за 5 днів (за замовчуванням: 500)"
    )
    @discord.app_commands.default_permissions(manage_roles=True)
    async def setup_activeping(self, interaction: discord.Interaction, role: discord.Role, min_level: int = 5, min_xp_5d: int = 500):
        """Налаштувати систему активних ролей"""
        
        
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
                    "min_xp_5d": min_xp_5d
                }
            },
            upsert=True
        )

        embed = discord.Embed(
            title="✅ Active Ping налаштовано!",
            description="Система активних ролей успішно налаштована",
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

    @discord.app_commands.command(name="activeping-disable", description="Вимкнути систему активних ролей")
    @discord.app_commands.default_permissions(manage_roles=True)
    async def disable_activeping(self, interaction: discord.Interaction):
        """Вимкнути систему активних ролей"""
        
        result = await db.settings.update_one(
            {"guild_id": str(interaction.guild.id)},
            {"$unset": {"active_role_id": "", "min_level": "", "min_xp_5d": ""}}
        )
        
        if result.modified_count > 0:
            embed = discord.Embed(
                title="✅ Систему вимкнено",
                description="Active Ping систему було успішно вимкнено",
                color=0x00ff00
            )
        else:
            embed = discord.Embed(
                title="ℹ️ Інформація",
                description="Active Ping система не була налаштована на цьому сервері",
                color=0xffaa00
            )
        
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="activeping-status", description="Показати поточні налаштування системи")
    @discord.app_commands.default_permissions(manage_roles=True)
    async def status_activeping(self, interaction: discord.Interaction):
        """Показати поточні налаштування"""
        
        setting = await db.settings.find_one({"guild_id": str(interaction.guild.id)})
        
        if not setting or "active_role_id" not in setting:
            embed = discord.Embed(
                title="ℹ️ Статус Active Ping",
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
            title="📊 Статус Active Ping",
            description="Поточні налаштування системи:",
            color=0x0099ff
        )
        embed.add_field(name="Роль:", value=role.mention, inline=True)
        embed.add_field(name="Мін. рівень:", value=str(setting.get("min_level", 5)), inline=True)
        embed.add_field(name="Мін. XP за 5 днів:", value=str(setting.get("min_xp_5d", 500)), inline=True)
        embed.add_field(name="Учасників з роллю:", value=str(len(role.members)), inline=True)
        
        await interaction.response.send_message(embed=embed)

    @discord.app_commands.command(name="activeping-check", description="Ручна перевірка активності всіх користувачів")
    @discord.app_commands.default_permissions(manage_roles=True)
    async def manual_check(self, interaction: discord.Interaction):
        """Ручна перевірка активності всіх користувачів"""
        
        setting = await db.settings.find_one({"guild_id": str(interaction.guild.id)})
        
        if not setting or "active_role_id" not in setting:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Active Ping система не налаштована на цьому сервері",
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

    async def _check_guild_active_roles(self, guild, setting):
        role_id = setting["active_role_id"]
        min_level = setting.get("min_level", 5)
        min_xp_5d = setting.get("min_xp_5d", 500)

        role = guild.get_role(role_id)
        if not role:
            return 0, 0

        cutoff_date = datetime.utcnow().date() - timedelta(days=5)

        added_count = 0
        removed_count = 0

        for member in guild.members:
            if member.bot:
                continue

            user_data = await db.users.find_one({"guild_id": str(guild.id), "user_id": str(member.id)})
            if not user_data:
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Inactive (no profile)")
                        removed_count += 1
                    except Exception:
                        pass
                continue

            level = user_data.get("level", 0)
            history = user_data.get("history", {})

            recent_xp = 0
            for i in range(5):
                day = (datetime.utcnow().date() - timedelta(days=i)).strftime("%Y-%m-%d")
                recent_xp += history.get(day, 0)

            has_role = role in member.roles


            if level >= min_level and recent_xp >= min_xp_5d:
                if not has_role:
                    try:
                        await member.add_roles(role, reason="Active player role assigned")
                        added_count += 1
                    except Exception:
                        pass
            else:
                if has_role:
                    try:
                        await member.remove_roles(role, reason="Active player role removed (inactive)")
                        removed_count += 1
                    except Exception:
                        pass

        return added_count, removed_count

    @tasks.loop(hours=24)
    async def check_active_roles(self):
       
        """Автоматична перевірка активних ролей кожні 24 години"""
       
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
    await bot.add_cog(ActivePingChecker(bot))
