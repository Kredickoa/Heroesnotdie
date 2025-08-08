import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict
from modules.db import get_database
from ._constants import RANKS, RANK_DESCRIPTIONS

db = get_database()

class LeaderboardCommand(commands.Cog):
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

    @app_commands.command(name="pidor_leaderboard", description="Показати таблицю лідерів")
    async def pidor_leaderboard_command(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        # Отримати топ-15 гравців
        top_players = await db.duel_stats.find(
            {"guild_id": interaction.guild.id}
        ).sort("wins", -1).limit(15).to_list(length=15)
        
        if not top_players:
            embed = discord.Embed(
                title="🏆 ТАБЛИЦЯ ЛІДЕРІВ",
                description="```\n📊 Ще ніхто не проводив дуелей на цьому сервері!\n\nВикористовуйте /pidor_duel щоб розпочати!```",
                color=0xF1C40F
            )
            await interaction.followup.send(embed=embed)
            return
        
        embed = discord.Embed(
            title="🏆 ТАБЛИЦЯ ЛІДЕРІВ",
            color=0xF1C40F
        )
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 12
        
        leaderboard_lines = ["📊 ТОП ДУЕЛЯНТІВ\n"]
        author_found = False
        
        for i, player_stats in enumerate(top_players):
            try:
                user = interaction.guild.get_member(int(player_stats['user_id']))
                if user:
                    rank_info = self.get_rank_info(player_stats['wins'])
                    win_rate = (player_stats['wins'] / max(player_stats['wins'] + player_stats['losses'], 1)) * 100
                    
                    line = (
                        f"{medals[i]} {user.display_name:<15} | "
                        f"{rank_info['emoji']} | "
                        f"W: {player_stats['wins']:<3} | "
                        f"WR: {win_rate:>5.1f}% | "
                        f"ПК: {player_stats['pk_balance']:<3}"
                    )
                    leaderboard_lines.append(line)
                    
                    if player_stats['user_id'] == str(interaction.user.id):
                        author_found = True
            except (ValueError, AttributeError):
                continue
        
        # Якщо автор не в топі, показати його позицію
        if not author_found:
            all_players = await db.duel_stats.find(
                {"guild_id": interaction.guild.id}
            ).sort("wins", -1).to_list(length=None)
            
            for i, player_stats in enumerate(all_players, 1):
                if player_stats['user_id'] == str(interaction.user.id):
                    rank_info = self.get_rank_info(player_stats['wins'])
                    win_rate = (player_stats['wins'] / max(player_stats['wins'] + player_stats['losses'], 1)) * 100
                    
                    line = (
                        f"\n--- ТИ НА {i} МІСЦІ ---\n"
                        f"🎯 {interaction.user.display_name} | "
                        f"{rank_info['emoji']} | "
                        f"W: {player_stats['wins']} | "
                        f"WR: {win_rate:.1f}% | "
                        f"ПК: {player_stats['pk_balance']}"
                    )
                    leaderboard_lines.append(line)
                    break
        
        embed.description = "```\n" + "\n".join(leaderboard_lines) + "\n```"
        
        # Статистика сервера
        total_duels = await db.duel_history.count_documents({"guild_id": interaction.guild.id})
        total_players = len(top_players)
        
        embed.set_footer(text=f"Всього дуелей: {total_duels} • Активних гравців: {total_players}")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(LeaderboardCommand(bot))