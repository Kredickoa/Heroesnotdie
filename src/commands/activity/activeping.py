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

    @commands.group(name="activeping", aliases=["ap"], invoke_without_command=True)
    @commands.has_permissions(manage_roles=True)
    async def activeping(self, ctx):
        """Керування системою активних ролей"""
        embed = discord.Embed(
            title="🎯 Active Ping System", 
            description="Система автоматичної видачі ролей активним гравцям",
            color=0x00ff00
        )
        embed.add_field(
            name="Команди:",
            value="`/activeping setup <роль> [мін_рівень] [мін_xp_5днів]` - Налаштувати систему\n"
                  "`/activeping disable` - Вимкнути систему\n"
                  "`/activeping status` - Поточні налаштування\n"
                  "`/activeping check` - Ручна перевірка активності",
            inline=False
        )
        embed.add_field(
            name="За замовчуванням:",
            value="Мінімальний рівень: **5**\nМінімум XP за 5 днів: **500**",
            inline=False
        )
        await ctx.send(embed=embed)

    @activeping.command(name="setup")
    @commands.has_permissions(manage_roles=True)
    async def setup_activeping(self, ctx, role: discord.Role, min_level: int = 5, min_xp_5d: int = 500):
        """Налаштувати систему активних ролей"""
        
        # Перевіряємо, чи бот може керувати цією роллю
        if role.position >= ctx.guild.me.top_role.position:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Роль знаходиться вище за мою найвищу роль! Перемістіть мою роль вище або оберіть іншу роль.",
                color=0xff0000
            )
            return await ctx.send(embed=embed)

        # Зберігаємо налаштування в базу даних
        await db.settings.update_one(
            {"guild_id": str(ctx.guild.id)},
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
            description=f"Система активних ролей успішно налаштована",
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
        
        await ctx.send(embed=embed)

    @activeping.command(name="disable")
    @commands.has_permissions(manage_roles=True)
    async def disable_activeping(self, ctx):
        """Вимкнути систему активних ролей"""
        
        result = await db.settings.update_one(
            {"guild_id": str(ctx.guild.id)},
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
        
        await ctx.send(embed=embed)

    @activeping.command(name="status")
    @commands.has_permissions(manage_roles=True)
    async def status_activeping(self, ctx):
        """Показати поточні налаштування"""
        
        setting = await db.settings.find_one({"guild_id": str(ctx.guild.id)})
        
        if not setting or "active_role_id" not in setting:
            embed = discord.Embed(
                title="ℹ️ Статус Active Ping",
                description="Система не налаштована на цьому сервері",
                color=0xffaa00
            )
            return await ctx.send(embed=embed)

        role = ctx.guild.get_role(setting["active_role_id"])
        if not role:
            embed = discord.Embed(
                title="⚠️ Помилка",
                description="Налаштована роль була видалена",
                color=0xff0000
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(
            title="📊 Статус Active Ping",
            description="Поточні налаштування системи:",
            color=0x0099ff
        )
        embed.add_field(name="Роль:", value=role.mention, inline=True)
        embed.add_field(name="Мін. рівень:", value=str(setting.get("min_level", 5)), inline=True)
        embed.add_field(name="Мін. XP за 5 днів:", value=str(setting.get("min_xp_5d", 500)), inline=True)
        embed.add_field(name="Учасників з роллю:", value=str(len(role.members)), inline=True)
        
        await ctx.send(embed=embed)

    @activeping.command(name="check")
    @commands.has_permissions(manage_roles=True)
    async def manual_check(self, ctx):
        """Ручна перевірка активності всіх користувачів"""
        
        setting = await db.settings.find_one({"guild_id": str(ctx.guild.id)})
        
        if not setting or "active_role_id" not in setting:
            embed = discord.Embed(
                title="❌ Помилка",
                description="Active Ping система не налаштована на цьому сервері",
                color=0xff0000
            )
            return await ctx.send(embed=embed)

        # Показуємо повідомлення про початок перевірки
        embed = discord.Embed(
            title="🔄 Перевірка активності",
            description="Починаю перевірку активності всіх користувачів...",
            color=0xffaa00
        )
        message = await ctx.send(embed=embed)

        # Запускаємо перевірку для цієї гільдії
        added, removed = await self._check_guild_active_roles(ctx.guild, setting)

        # Оновлюємо повідомлення з результатами
        embed = discord.Embed(
            title="✅ Перевірку завершено",
            description="Результати ручної перевірки активності:",
            color=0x00ff00
        )
        embed.add_field(name="Додано ролей:", value=str(added), inline=True)
        embed.add_field(name="Знято ролей:", value=str(removed), inline=True)
        
        await message.edit(embed=embed)

    async def _check_guild_active_roles(self, guild, setting):
        """Перевірка активних ролей для конкретної гільдії"""
        role_id = setting["active_role_id"]
        min_level = setting.get("min_level", 5)
        min_xp_5d = setting.get("min_xp_5d", 500)

        role = guild.get_role(role_id)
        if not role:
            return 0, 0

        # Дата 5 днів тому
        cutoff_date = datetime.utcnow() - timedelta(days=5)
        
        added_count = 0
        removed_count = 0

        # Перебираємо учасників гільдії
        for member in guild.members:
            if member.bot:
                continue

            # Отримуємо профіль користувача
            profile = await db.profiles.find_one({"user_id": str(member.id)})
            if not profile:
                # Якщо немає профілю, знімаємо роль, якщо є
                if role in member.roles:
                    try:
                        await member.remove_roles(role, reason="Inactive (no profile)")
                        removed_count += 1
                    except Exception:
                        pass
                continue

            level = profile.get("level", 0)
            xp_history = profile.get("xp_history", [])

            # Сумуємо XP за останні 5 днів
            recent_xp = 0
            for entry in xp_history:
                date_str = entry.get("date")
                if not date_str:
                    continue
                try:
                    date_obj = datetime.fromisoformat(date_str)
                    if date_obj >= cutoff_date:
                        recent_xp += entry.get("xp", 0)
                except ValueError:
                    continue

            # Логіка видачі ролі
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
        # Отримуємо всі гільдії з налаштуваннями activeping
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

    @setup_activeping.error
    @disable_activeping.error
    @status_activeping.error
    @manual_check.error
    async def activeping_error(self, ctx, error):
        if isinstance(error, commands.MissingPermissions):
            embed = discord.Embed(
                title="❌ Недостатньо прав",
                description="Для використання цієї команди потрібне право **Керування ролями**",
                color=0xff0000
            )
            await ctx.send(embed=embed)
        elif isinstance(error, commands.RoleNotFound):
            embed = discord.Embed(
                title="❌ Роль не знайдено",
                description="Вказана роль не існує на цьому сервері",
                color=0xff0000
            )
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(ActivePingChecker(bot))