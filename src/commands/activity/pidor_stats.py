import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict
from modules.db import get_database
from .constants import RANKS, RANK_DESCRIPTIONS

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