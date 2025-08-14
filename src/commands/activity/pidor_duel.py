import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional, Dict, List
from modules.db import get_database
from ._constants import RANKS, RANK_DESCRIPTIONS, SHOP_ITEMS, RANDOM_EVENTS
from .views import DuelRequestView, DuelBattleView

db = get_database()

class PidorDuelCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}
        self.daily_limits = {}

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

    def check_cooldown(self, user_id: int) -> bool:
        """Перевірити кулдаун гравця"""
        if user_id in self.cooldowns:
            time_diff = datetime.now() - self.cooldowns[user_id]
            return time_diff.total_seconds() >= 30
        return True

    async def check_daily_limit(self, user_id: int, guild_id: int) -> bool:
        """Перевірити щоденний ліміт ПК"""
        today = datetime.now().date().isoformat()
        stats = await self.get_user_stats(user_id, guild_id)
        
        if stats.get("last_pk_date") != today:
            await db.duel_stats.update_one(
                {"user_id": str(user_id), "guild_id": guild_id},
                {"$set": {"daily_pk": 0, "last_pk_date": today}}
            )
            return True
        
        return stats.get("daily_pk", 0) < 100

    async def execute_duel(self, interaction, challenger, target):
        """Виконати дуель між двома гравцями"""
        guild_id = interaction.guild.id
        
        # Отримати статистику гравців
        challenger_stats = await self.get_user_stats(challenger.id, guild_id)
        target_stats = await self.get_user_stats(target.id, guild_id)
        
        # Перевірити випадкову подію (5-7% шанс)
        event_chance = random.uniform(5, 7)
        random_event = None
        event_effects = {}
        
        if random.random() * 100 < event_chance:
            random_event = random.choice(RANDOM_EVENTS)
            
            # Показати подію
            event_embed = discord.Embed(
                title="🎲 ВИПАДКОВА ПОДІЯ!",
                description=f"**{random_event['name']}**\n{random_event['description']}",
                color=0xE67E22
            )
            await interaction.edit_original_response(embed=event_embed)
            await asyncio.sleep(3)
            
            # Обробити ефекти події
            if random_event["name"] == "DDoS атака":
                await interaction.edit_original_response(
                    embed=discord.Embed(
                        title="💥 DDoS АТАК!",
                        description="Дуель повторюється через 10 секунд...",
                        color=0xE74C3C
                    )
                )
                await asyncio.sleep(10)
                return await self.execute_duel(interaction, challenger, target)
            
            elif random_event["name"] == "Втручання модератора":
                event_effects["random_winner"] = True
            elif random_event["name"] == "Читерський софт":
                lucky_player = random.choice([challenger, target])
                event_effects["accuracy_boost"] = {lucky_player.id: 25}
            elif random_event["name"] == "Алкогольне отруєння":
                unlucky_player = random.choice([challenger, target])
                event_effects["accuracy_penalty"] = {unlucky_player.id: 15}

        # Визначити першого стрільця
        first_shooter = random.choice([challenger, target])
        second_shooter = target if first_shooter == challenger else challenger
        luck_bonus = random.choice([challenger, target])
        
        # Показати початок дуелі
        battle_embed = discord.Embed(
            title="⚔️ ДУЕЛЬ РОЗПОЧАТО!",
            description=f"<:dart:1405489296411988040> **{first_shooter.mention}** стріляє першим!",
            color=0xE74C3C
        )
        
        challenger_rank = self.get_rank_info(challenger_stats['wins'])
        target_rank = self.get_rank_info(target_stats['wins'])
        
        battle_embed.add_field(
            name=f"{challenger_rank['emoji']} Челленджер",
            value=f"**{challenger.display_name}**\n<:trophy:1405488585372860517> Перемоги: {challenger_stats['wins']}",
            inline=True
        )
        
        battle_embed.add_field(
            name="🆚", 
            value="**VS**", 
            inline=True
        )
        
        battle_embed.add_field(
            name=f"{target_rank['emoji']} Опонент",
            value=f"**{target.display_name}**\n<:trophy:1405488585372860517> Перемоги: {target_stats['wins']}",
            inline=True
        )
        
        if random_event:
            battle_embed.add_field(
                name="🎲 Активна подія",
                value=f"**{random_event['name']}**",
                inline=False
            )
        
        battle_embed.add_field(
            name="🍀 Рандомна задишка",
            value=f"{luck_bonus.mention} отримує +10% до шансу!",
            inline=False
        )
        
        battle_embed.set_footer(text="Стріляй поки не пізно!")
        
        # Підготувати дані для бою
        battle_info = {
            "challenger": challenger,
            "target": target, 
            "first_shooter": first_shooter,
            "second_shooter": second_shooter,
            "event_effects": event_effects,
            "luck_bonus": luck_bonus,
            "random_event": random_event,
            "guild_id": guild_id
        }
        
        # Створити view з кнопкою пострілу
        view = DuelBattleView(first_shooter, second_shooter, battle_info, self, interaction)
        
        await interaction.edit_original_response(embed=battle_embed, view=view)

    async def process_shot(self, interaction, shooter, opponent, battle_info, first_shot=True, auto_miss=False):
        """Обробити постріл гравця"""
        
        # Розрахувати точність
        accuracy = 50
        
        # Застосувати ефекти подій
        event_effects = battle_info.get("event_effects", {})
        if "accuracy_boost" in event_effects and shooter.id in event_effects["accuracy_boost"]:
            accuracy += event_effects["accuracy_boost"][shooter.id]
        if "accuracy_penalty" in event_effects and shooter.id in event_effects["accuracy_penalty"]:
            accuracy -= event_effects["accuracy_penalty"][shooter.id]
        
        # Задишка
        if battle_info.get("luck_bonus") == shooter:
            accuracy += 10
        
        # Визначити результат пострілу
        hit = not auto_miss and random.random() * 100 < accuracy
        
        if hit or event_effects.get("random_winner"):
            # Влучання - гра закінчена
            winner = shooter
            loser = opponent
            
            if event_effects.get("random_winner"):
                winner, loser = random.choice([(battle_info["challenger"], battle_info["target"]), 
                                             (battle_info["target"], battle_info["challenger"])])
                result_text = f"🛡️ **Модератор втрутився!** {winner.mention} перемiг!"
            else:
                result_text = f"<:dart:1405489296411988040> **{winner.mention}** влучно стріляв! Переможець визначений!"
            
            await self.finish_duel(interaction, winner, loser, battle_info, result_text)
            
        else:
            # Промах - черга переходить до іншого гравця
            if first_shot:
                miss_embed = discord.Embed(
                    title="💥 ПРОМАХ!",
                    description=f"**{shooter.mention}** промахнувся!\nЧерга переходить до **{opponent.mention}**!",
                    color=0xF39C12
                )
                
                # Створити нову кнопку для другого стрільця
                view = DuelBattleView(opponent, shooter, battle_info, self, interaction)
                await interaction.edit_original_response(embed=miss_embed, view=view)
            else:
                # Обидва промахнулися - випадковий переможець
                winner, loser = random.choice([(battle_info["challenger"], battle_info["target"]),
                                             (battle_info["target"], battle_info["challenger"])])
                result_text = f"😅 **Обидва промахнулися!** Але **{winner.mention}** виявився спритнішим!"
                
                await self.finish_duel(interaction, winner, loser, battle_info, result_text)

    async def finish_duel(self, interaction, winner, loser, battle_info, battle_text):
        """Завершити дуель та оновити статистику"""
        guild_id = battle_info["guild_id"]
        
        # Отримати статистику
        winner_stats = await self.get_user_stats(winner.id, guild_id)
        loser_stats = await self.get_user_stats(loser.id, guild_id)
        
        winner_rank = self.get_rank_info(winner_stats['wins'])
        loser_rank = self.get_rank_info(loser_stats['wins'])
        
        # Розрахувати ПК
        pk_gained = winner_rank['win_reward']
        pk_lost = loser_rank['loss_penalty']
        
        # Перевірити щоденний ліміт
        winner_can_earn = await self.check_daily_limit(winner.id, guild_id)
        if not winner_can_earn:
            pk_gained = 0

        # Оновити баланс
        new_winner_balance = min(winner_stats['pk_balance'] + pk_gained, 1000)
        new_loser_balance = max(loser_stats['pk_balance'] - pk_lost, 0)
        
        # Оновити базу даних
        await db.duel_stats.update_one(
            {"user_id": str(winner.id), "guild_id": guild_id},
            {
                "$inc": {"wins": 1, "daily_pk": pk_gained},
                "$set": {"pk_balance": new_winner_balance}
            }
        )
        
        await db.duel_stats.update_one(
            {"user_id": str(loser.id), "guild_id": guild_id},
            {
                "$inc": {"losses": 1},
                "$set": {"pk_balance": new_loser_balance}
            }
        )
        
        # Зберегти історію
        await db.duel_history.insert_one({
            "guild_id": guild_id,
            "winner": str(winner.id),
            "loser": str(loser.id),
            "pk_change": {"winner": pk_gained, "loser": pk_lost},
            "event": battle_info.get("random_event", {}).get("name") if battle_info.get("random_event") else None,
            "timestamp": datetime.utcnow()
        })
        
        # Оновити кулдауни
        self.cooldowns[battle_info["challenger"].id] = datetime.now()
        self.cooldowns[battle_info["target"].id] = datetime.now()

        # Показати результат
        result_embed = discord.Embed(
            title="🏆 РЕЗУЛЬТАТ ДУЕЛІ",
            description=battle_text,
            color=0x2ECC71
        )
        
        result_embed.add_field(
            name="🥇 Переможець",
            value=f"**{winner.mention}**\n+{pk_gained} ПК\n<:bank:1405489965244088340> Баланс: {new_winner_balance} ПК",
            inline=True
        )
        
        result_embed.add_field(
            name="💀 Переможений",
            value=f"**{loser.mention}**\n-{pk_lost} ПК\n<:bank:1405489965244088340> Баланс: {new_loser_balance} ПК",
            inline=True
        )
        
        meme_comments = [
            "Епічна битва віків!",
            "Це було неочікувано!",
            "Хтось викликає швидку?",
            "Мама, я в телевізорі!",
            "Красиво зіграв!",
            "Чекай реванш!",
            "Це була легка перемога!",
            "Повний розгром!",
            "Майже як у кіно!",
            "Професіонал у дії!"
        ]
        
        result_embed.set_footer(text=random.choice(meme_comments))
        
        await interaction.edit_original_response(embed=result_embed, view=None)

    @app_commands.command(name="pidor_duel", description="Викликати користувача на дуель")
    @app_commands.describe(user="Кого викликати на дуель (опціонально - буде обрано рандомного гравця)")
    async def pidor_duel_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        challenger = interaction.user
        
        # Перевірити кулдаун
        if not self.check_cooldown(challenger.id):
            remaining = 30 - (datetime.now() - self.cooldowns[challenger.id]).total_seconds()
            await interaction.response.send_message(
                f"⏰ Кулдаун! Почекай ще {int(remaining)} секунд.",
                ephemeral=True
            )
            return
        
        # Перевірити щоденний ліміт
        if not await self.check_daily_limit(challenger.id, interaction.guild.id):
            await interaction.response.send_message(
                "📈 Досягнуто щоденний ліміт ПК (100/день). Спробуй завтра!",
                ephemeral=True
            )
            return
        
        # Визначити опонента
        if user:
            target = user
        else:
            # Рандомний опонент
            candidates = [
                m for m in interaction.guild.members 
                if not m.bot and m != challenger and m.status != discord.Status.offline
            ]
            if not candidates:
                await interaction.response.send_message(
                    "😴 Немає доступних гравців для дуелі.",
                    ephemeral=True
                )
                return
            target = random.choice(candidates)
        
        if target == challenger:
            await interaction.response.send_message(
                "🤡 Не можна викликати себе на дуель, генію!",
                ephemeral=True
            )
            return
        
        if target.bot:
            await interaction.response.send_message(
                "🤖 Боти не дуелюються. Вони зайняті розумною діяльністю.",
                ephemeral=True
            )
            return
        
        # Створити запит на дуель
        view = DuelRequestView(challenger, target)
        
        challenger_stats = await self.get_user_stats(challenger.id, interaction.guild.id)
        target_stats = await self.get_user_stats(target.id, interaction.guild.id)
        
        challenger_rank = self.get_rank_info(challenger_stats['wins'])
        target_rank = self.get_rank_info(target_stats['wins'])
        
        embed = discord.Embed(
            title="⚔️ ВИКЛИК НА ДУЕЛЬ!",
            description=f"<:pistol:1405488178978095246> {challenger.mention} викликає {target.mention} на дуель!",
            color=0xE67E22
        )
        
        embed.add_field(
            name=f"{challenger_rank['emoji']} Челленджер",
            value=f"**{challenger.display_name}**\n{challenger_rank['name']}\n<:trophy:1405488585372860517> Перемоги: {challenger_stats['wins']}",
            inline=True
        )
        
        embed.add_field(
            name=f"{target_rank['emoji']} Опонент", 
            value=f"**{target.display_name}**\n{target_rank['name']}\n<:trophy:1405488585372860517> Перемоги: {target_stats['wins']}",
            inline=True
        )
        
        embed.set_footer(text="У опонента є 60 секунд щоб відповісти!")
        
        await interaction.response.send_message(
            content=f"{target.mention}, тебе викликають на дуель!",
            embed=embed,
            view=view
        )

async def setup(bot):
    await bot.add_cog(PidorDuelCommand(bot))