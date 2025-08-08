import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict
from modules.db import get_database
from ._constants import RANKS, RANK_DESCRIPTIONS

db = get_database()

class PidorStatsCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_rank_info(self, wins: int) -> Dict:
        """Визначити ранг гравця за кількістю перемог"""
        for i, rank in enumerate(RANKS):
            if rank["min_wins"] <= wins <= rank["max_wins"]:
                rank_copy = rank.copy()
                rank_copy["description"] = RANK_DESCRIPTIONS[i]
                return rank_copy
        return RANKS[-1]

    @app_commands.command(name="pidor_stats", description="Показати статистику дуелей сервера")
    async def pidor_stats_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        # Загальна статистика сервера
        total_duels = await db.duel_history.count_documents({"guild_id": interaction.guild.id})
        total_players = await db.duel_stats.count_documents({"guild_id": interaction.guild.id})
        
        # Найактивніший гравець
        most_active = await db.duel_stats.find_one(
            {"guild_id": interaction.guild.id},
            sort=[("wins", -1), ("losses", -1)]
        )
        
        # Найбагатший гравець
        richest_player = await db.duel_stats.find_one(
            {"guild_id": interaction.guild.id},
            sort=[("pk_balance", -1)]
        )
        
        # Статистика за останній тиждень
        from datetime import datetime, timedelta
        week_ago = datetime.utcnow() - timedelta(days=7)
        recent_duels = await db.duel_history.count_documents({
            "guild_id": interaction.guild.id,
            "timestamp": {"$gte": week_ago}
        })
        
        embed = discord.Embed(
            title="📊 СТАТИСТИКА СЕРВЕРА",
            color=0x3498DB
        )
        
        # Загальна статистика
        embed.add_field(
            name="🎯 Загальна статистика",
            value=f"```\n⚔️ Всього дуелей: {total_duels}\n👥 Активних гравців: {total_players}\n📅 Дуелей за тиждень: {recent_duels}```",
            inline=False
        )
        
        # Найактивніший гравець
        if most_active:
            try:
                most_active_user = interaction.guild.get_member(int(most_active['user_id']))
                if most_active_user:
                    rank_info = self.get_rank_info(most_active['wins'])
                    total_battles = most_active['wins'] + most_active['losses']
                    win_rate = (most_active['wins'] / max(total_battles, 1)) * 100
                    
                    embed.add_field(
                        name="🏆 Найактивніший гравець",
                        value=f"```\n{most_active_user.display_name}\n{rank_info['emoji']} {rank_info['name']}\n⚔️ Битв: {total_battles}\n🎯 Він-рейт: {win_rate:.1f}%```",
                        inline=True
                    )
            except (ValueError, AttributeError):
                pass
        
        # Найбагатший гравець
        if richest_player:
            try:
                richest_user = interaction.guild.get_member(int(richest_player['user_id']))
                if richest_user:
                    embed.add_field(
                        name="💰 Найбагатший гравець",
                        value=f"```\n{richest_user.display_name}\n💎 {richest_player['pk_balance']} ПК\n🎒 Предметів: {len(richest_player.get('items', []))}```",
                        inline=True
                    )
            except (ValueError, AttributeError):
                pass
        
        # Розподіл за рангами
        rank_distribution = {}
        async for player in db.duel_stats.find({"guild_id": interaction.guild.id}):
            rank_info = self.get_rank_info(player['wins'])
            rank_name = rank_info['name']
            rank_distribution[rank_name] = rank_distribution.get(rank_name, 0) + 1
        
        if rank_distribution:
            rank_text = "```\n"
            for rank in RANKS:
                count = rank_distribution.get(rank['name'], 0)
                if count > 0:
                    rank_text += f"{rank['emoji']} {rank['name']}: {count}\n"
            rank_text += "```"
            
            embed.add_field(
                name="📈 Розподіл за рангами",
                value=rank_text,
                inline=False
            )
        
        # Середні показники
        if total_players > 0:
            pipeline = [
                {"$match": {"guild_id": interaction.guild.id}},
                {"$group": {
                    "_id": None,
                    "avg_wins": {"$avg": "$wins"},
                    "avg_balance": {"$avg": "$pk_balance"},
                    "total_pk": {"$sum": "$pk_balance"}
                }}
            ]
            
            avg_stats = await db.duel_stats.aggregate(pipeline).to_list(length=1)
            if avg_stats:
                stats = avg_stats[0]
                embed.add_field(
                    name="📊 Середні показники",
                    value=f"```\n🏆 Середньо перемог: {stats['avg_wins']:.1f}\n💰 Середній баланс: {stats['avg_balance']:.0f} ПК\n💎 Всього ПК в економіці: {stats['total_pk']:.0f}```",
                    inline=False
                )
        
        embed.set_footer(text="Статистика оновлюється в реальному часі")
        embed.set_thumbnail(url=interaction.guild.icon.url if interaction.guild.icon else None)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PidorStatsCommand(bot))