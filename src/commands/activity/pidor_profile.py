import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict
from modules.db import get_database
 from ._constants import RANKS, RANK_DESCRIPTIONS, SHOP_ITEMS
from .views import ProfileView

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

    async def buy_item_inline(self, interaction, item_id: str):
        """Купити предмет в магазині"""
        user_stats = await self.get_user_stats(interaction.user.id, interaction.guild.id)
        item = SHOP_ITEMS[item_id]
        
        # Перевірити баланс
        if user_stats['pk_balance'] < item['price']:
            await interaction.response.send_message(
                f"❌ Недостатньо ПК! Потрібно {item['price']} ПК, а у вас {user_stats['pk_balance']} ПК.",
                ephemeral=True
            )
            return False
        
        # Перевірити слоти інвентарю
        max_slots = 1 + (user_stats['wins'] // 10)
        if len(user_stats['items']) >= max_slots:
            await interaction.response.send_message(
                f"❌ Інвентар заповнений! Доступно слотів: {max_slots}",
                ephemeral=True
            )
            return False
        
        # Купити предмет
        new_balance = user_stats['pk_balance'] - item['price']
        new_items = user_stats['items'] + [item_id]
        
        await db.duel_stats.update_one(
            {"user_id": str(interaction.user.id), "guild_id": interaction.guild.id},
            {
                "$set": {
                    "pk_balance": new_balance,
                    "items": new_items
                }
            }
        )
        
        await interaction.followup.send(
            f"✅ Куплено **{item['name']}** за {item['price']} ПК!\n"
            f"Новий баланс: {new_balance} ПК",
            ephemeral=True
        )
        return True

    @app_commands.command(name="pidor_profile", description="Показати профіль гравця з інвентарем та магазином")
    @app_commands.describe(user="Чий профіль показати (за замовчуванням - свій)")
    async def pidor_profile_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target_user = user or interaction.user
        
        view = ProfileView(interaction.user, target_user)
        embed = await view.get_profile_embed(interaction)
        await view.update_view(interaction)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

async def setup(bot):
    await bot.add_cog(ProfileCommand(bot))