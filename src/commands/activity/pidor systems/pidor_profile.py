import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict, List
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import io
import asyncio
from modules.db import get_database
from ._constants import RANKS, RANK_DESCRIPTIONS

db = get_database()

class ProfileCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_user_stats(self, user_id: int, guild_id: int) -> Dict:
        """Отримати статистику користувача"""
        stats = await db.duel_stats.find_one({"user_id": str(user_id), "guild_id": guild_id})
        if not stats:
            stats = {
                "user_id": str(user_id),
                "guild_id": guild_id,
                "wins": 0,
                "losses": 0,
                "pk_balance": 0,
                "items": [],
                "debuffs": {},
                "daily_pk": 0,
                "last_pk_date": None
            }
            await db.duel_stats.insert_one(stats)
        return stats

    def get_rank_info(self, wins: int) -> Dict:
        """Визначити ранг гравця за кількістю перемог"""
        for i, rank in enumerate(RANKS):
            if rank["min_wins"] <= wins <= rank["max_wins"]:
                rank_copy = rank.copy()
                rank_copy["description"] = RANK_DESCRIPTIONS[i]
                return rank_copy
        return RANKS[-1]

    async def get_user_activity(self, user_id: int, guild_id: int) -> List[Dict]:
        """Отримати активність користувача за останні 7 днів"""
        week_ago = datetime.utcnow() - timedelta(days=7)
        
        # Отримати дуелі за тиждень
        duels = await db.duel_history.find({
            "guild_id": guild_id,
            "timestamp": {"$gte": week_ago},
            "$or": [
                {"winner": str(user_id)},
                {"loser": str(user_id)}
            ]
        }).sort("timestamp", 1).to_list(length=None)
        
        # Групування по днях
        daily_activity = {}
        for i in range(7):
            date = (datetime.utcnow() - timedelta(days=6-i)).date()
            daily_activity[date] = 0
        
        for duel in duels:
            date = duel['timestamp'].date()
            if date in daily_activity:
                if duel['winner'] == str(user_id):
                    daily_activity[date] += 50  # XP за перемогу
                else:
                    daily_activity[date] += 25  # XP за участь
        
        return [(date, xp) for date, xp in daily_activity.items()]

    async def create_activity_chart(self, user_id: int, guild_id: int, username: str) -> io.BytesIO:
        """Створити графік активності"""
        activity = await self.get_user_activity(user_id, guild_id)
        
        if not activity:
            return None
        
        # Налаштування matplotlib
        plt.style.use('dark_background')
        fig, ax = plt.subplots(figsize=(10, 4), facecolor='#2C2F33')
        ax.set_facecolor('#2C2F33')
        
        dates = [item[0] for item in activity]
        xp_values = [item[1] for item in activity]
        
        # Створити графік
        ax.plot(dates, xp_values, color='#7289DA', linewidth=3, marker='o', markersize=8, markerfacecolor='#7289DA')
        ax.fill_between(dates, xp_values, alpha=0.3, color='#7289DA')
        
        # Налаштування осей
        ax.set_title(f"Активність (XP за останні 7 днів)", color='#FFFFFF', fontsize=14, fontweight='bold', pad=20)
        ax.set_xlabel("День тижня", color='#B9BBBE', fontsize=10)
        ax.set_ylabel("Отримано XP", color='#B9BBBE', fontsize=10)
        
        # Форматування дат
        day_names = ['Sat', 'Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri']
        ax.set_xticks(dates)
        ax.set_xticklabels(day_names, color='#B9BBBE')
        
        # Налаштування сітки
        ax.grid(True, alpha=0.3, color='#4F545C')
        ax.spines['bottom'].set_color('#4F545C')
        ax.spines['top'].set_color('#4F545C')
        ax.spines['right'].set_color('#4F545C')
        ax.spines['left'].set_color('#4F545C')
        
        # Колір тексту
        ax.tick_params(colors='#B9BBBE')
        
        plt.tight_layout()
        
        # Зберегти в BytesIO
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', facecolor='#2C2F33', edgecolor='none', dpi=150)
        buffer.seek(0)
        plt.close()
        
        return buffer

    class ProfileStatsView(discord.ui.View):
        def __init__(self, user, target_user, profile_cog):
            super().__init__(timeout=300)
            self.user = user
            self.target_user = target_user
            self.profile_cog = profile_cog
            self.current_page = "profile"

        async def get_profile_embed(self, interaction):
            stats = await self.profile_cog.get_user_stats(self.target_user.id, interaction.guild.id)
            rank_info = self.profile_cog.get_rank_info(stats['wins'])
            
            embed = discord.Embed(color=0x7289DA)
            
            # Профіль хедер
            embed.set_author(
                name=f"{rank_info['emoji']} {self.target_user.display_name}",
                icon_url=self.target_user.display_avatar.url
            )
            
            # Основна інформація в одному полі
            total_battles = stats['wins'] + stats['losses']
            win_rate = (stats['wins'] / max(total_battles, 1)) * 100 if total_battles > 0 else 0
            
            profile_info = f"""
            **Рівень:** 28 | **XP:** 4378 / 5420 (81%)
            **Voice:** 1809 хв | **Реакцій:** 636 | **Повідомлень:** 1328
            
            **Ролі:** Admin, 750 hours, Ukr
            """
            
            embed.add_field(name="📊 Статистика", value=profile_info, inline=False)
            
            # Статистика дуелей
            duel_info = f"""
            ```
            ⚔️ Перемоги: {stats['wins']}
            💀 Поразки: {stats['losses']}
            📈 Він-рейт: {win_rate:.1f}%
            💰 Баланс: {stats['pk_balance']} ПК
            ```
            """
            
            embed.add_field(name="🎯 Дуельна статистика", value=duel_info, inline=True)
            
            # Ранг та опис
            embed.add_field(
                name=f"🏆 {rank_info['name']}",
                value=f"*{rank_info['description']}*",
                inline=True
            )
            
            embed.set_footer(text=f"Участник з: 22 June 2025")
            embed.set_thumbnail(url=self.target_user.display_avatar.url)
            
            return embed

        async def get_stats_embed(self, interaction):
            stats = await self.profile_cog.get_user_stats(self.target_user.id, interaction.guild.id)
            
            embed = discord.Embed(
                title="📈 ДЕТАЛЬНА СТАТИСТИКА",
                color=0x3498DB
            )
            
            embed.set_author(
                name=self.target_user.display_name,
                icon_url=self.target_user.display_avatar.url
            )
            
            # Загальна статистика
            total_battles = stats['wins'] + stats['losses']
            win_rate = (stats['wins'] / max(total_battles, 1)) * 100 if total_battles > 0 else 0
            
            general_stats = f"""
            ```
            📊 Загальна статистика
            ⚔️ Всього битв: {total_battles}
            🏆 Перемоги: {stats['wins']}
            💀 Поразки: {stats['losses']}
            📈 Він-рейт: {win_rate:.1f}%
            💰 Поточний баланс: {stats['pk_balance']} ПК
            🎒 Предметів: {len(stats.get('items', []))}
            ```
            """
            embed.add_field(name="📋 Основні показники", value=general_stats, inline=False)
            
            # Статистика за тиждень
            week_stats = await self.get_week_stats(interaction)
            embed.add_field(name="📅 За останній тиждень", value=week_stats, inline=True)
            
            # Рейтинг на сервері
            server_rank = await self.get_server_rank(interaction)
            embed.add_field(name="🏅 Позиція на сервері", value=server_rank, inline=True)
            
            embed.set_footer(text="Статистика оновлюється в реальному часі")
            
            return embed

        async def get_week_stats(self, interaction):
            week_ago = datetime.utcnow() - timedelta(days=7)
            
            week_duels = await db.duel_history.count_documents({
                "guild_id": interaction.guild.id,
                "timestamp": {"$gte": week_ago},
                "$or": [
                    {"winner": str(self.target_user.id)},
                    {"loser": str(self.target_user.id)}
                ]
            })
            
            week_wins = await db.duel_history.count_documents({
                "guild_id": interaction.guild.id,
                "timestamp": {"$gte": week_ago},
                "winner": str(self.target_user.id)
            })
            
            week_win_rate = (week_wins / max(week_duels, 1)) * 100 if week_duels > 0 else 0
            
            return f"""
            ```
            ⚔️ Битв: {week_duels}
            🏆 Перемог: {week_wins}
            📈 Він-рейт: {week_win_rate:.1f}%
            ```
            """

        async def get_server_rank(self, interaction):
            all_players = await db.duel_stats.find(
                {"guild_id": interaction.guild.id}
            ).sort("wins", -1).to_list(length=None)
            
            user_rank = None
            for i, player in enumerate(all_players, 1):
                if player['user_id'] == str(self.target_user.id):
                    user_rank = i
                    break
            
            total_players = len(all_players)
            
            return f"""
            ```
            🏅 Позиція: {user_rank or 'N/A'} з {total_players}
            📊 Топ {((user_rank / total_players) * 100):.0f}%
            ```
            """ if user_rank else "```\nНе брав участі в дуелях\n```"

        async def update_view(self, interaction):
            self.clear_items()
            
            # Кнопки навігації
            profile_btn = discord.ui.Button(
                label="👤 Профіль",
                style=discord.ButtonStyle.primary if self.current_page == "profile" else discord.ButtonStyle.secondary,
                disabled=self.current_page == "profile"
            )
            profile_btn.callback = self.show_profile
            self.add_item(profile_btn)

            stats_btn = discord.ui.Button(
                label="📊 Статистика", 
                style=discord.ButtonStyle.primary if self.current_page == "stats" else discord.ButtonStyle.secondary,
                disabled=self.current_page == "stats"
            )
            stats_btn.callback = self.show_stats
            self.add_item(stats_btn)

        async def show_profile(self, interaction):
            self.current_page = "profile"
            embed = await self.get_profile_embed(interaction)
            await self.update_view(interaction)
            
            # Створити та додати графік
            chart_buffer = await self.profile_cog.create_activity_chart(
                self.target_user.id, 
                interaction.guild.id, 
                self.target_user.display_name
            )
            
            if chart_buffer:
                file = discord.File(chart_buffer, filename="activity.png")
                embed.set_image(url="attachment://activity.png")
                await interaction.response.edit_message(embed=embed, view=self, attachments=[file])
            else:
                await interaction.response.edit_message(embed=embed, view=self, attachments=[])

        async def show_stats(self, interaction):
            self.current_page = "stats"
            embed = await self.get_stats_embed(interaction)
            await self.update_view(interaction)
            await interaction.response.edit_message(embed=embed, view=self, attachments=[])

    @app_commands.command(name="pidor_profile", description="Показати профіль гравця")
    @app_commands.describe(user="Чий профіль показати (за замовчуванням - свій)")
    async def pidor_profile_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        
        target_user = user or interaction.user
        view = self.ProfileStatsView(interaction.user, target_user, self)
        
        embed = await view.get_profile_embed(interaction)
        await view.update_view(interaction)
        
        # Створити графік активності
        chart_buffer = await self.create_activity_chart(
            target_user.id, 
            interaction.guild.id, 
            target_user.display_name
        )
        
        if chart_buffer:
            file = discord.File(chart_buffer, filename="activity.png")
            embed.set_image(url="attachment://activity.png")
            await interaction.followup.send(embed=embed, view=view, file=file)
        else:
            await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ProfileCommand(bot))