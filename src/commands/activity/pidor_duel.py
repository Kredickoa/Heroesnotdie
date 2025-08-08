import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
import asyncio
from typing import Optional, Dict, List
from modules.db import get_database

db = get_database()

# Константи системи
RANKS = [
    {"name": "Щойно з пологового", "emoji": "👶", "min_wins": 0, "max_wins": 9, "win_reward": 8, "loss_penalty": 2},
    {"name": "Призовник ЗСУ", "emoji": "🪖", "min_wins": 10, "max_wins": 19, "win_reward": 7, "loss_penalty": 5},
    {"name": "Ветеран з 2014-го", "emoji": "💀", "min_wins": 20, "max_wins": 49, "win_reward": 6, "loss_penalty": 8},
    {"name": "Бог локалки", "emoji": "👑", "min_wins": 50, "max_wins": 999999, "win_reward": 5, "loss_penalty": 10},
]

RANK_DESCRIPTIONS = [
    "ходить з дерев'яним мечем і впевнений, що топ-1 через тиждень",
    "вже знає, що таке поразка, але все ще біжить з голими руками на босів",
    "пам'ятає старі патчі, коли +10 ПК давали за чих, і розказує про це всім",
    "усі бояться кидати йому дуель, а він боїться програти рандому з палкою"
]

SHOP_ITEMS = {
    "armor": {"name": "Бронежилет", "price": 45, "buff": "+1 життя", "debuff": "-10% точності"},
    "golden_bullet": {"name": "Золота куля", "price": 80, "buff": "100% влучання", "debuff": "-20% точності після"},
    "vodka": {"name": "Горілка", "price": 25, "buff": "Знімає дебафи", "debuff": "30% шанс тремтіння рук"},
    "machinegun": {"name": "Кулемет", "price": 120, "buff": "3 постріли підряд", "debuff": "-40% точності після"},
    "casino": {"name": "Казино-рулетка", "price": 15, "buff": "50% шанс на баф", "debuff": "50% шанс на дебаф"},
    "admin_bribe": {"name": "Підкуп адміна", "price": 200, "buff": "Автоперемога", "debuff": "-50% точності 3 бої"}
}

RANDOM_EVENTS = [
    {"name": "Лаг сервера", "description": "Обидва гравці отримують +20% шанс на перемогу", "chance": 1},
    {"name": "Читерський софт", "description": "Один гравець отримує +25% до влучання", "chance": 1.5},
    {"name": "Алкогольне отруєння", "description": "Один гравець отримує тремтіння рук", "chance": 1.5},
    {"name": "Втручання модератора", "description": "Переможець визначається випадково", "chance": 1},
    {"name": "DDoS атака", "description": "Дуель повторюється через 10 секунд", "chance": 1}
]

class DuelRequestView(discord.ui.View):
    def __init__(self, challenger, target, timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.target = target

    @discord.ui.button(label="⚔️ Прийняти дуель", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("❌ Це не твій дуель!", ephemeral=True)
            return
        
        await interaction.response.edit_message(
            content="⚔️ **Дуель розпочато!** Підготовка...",
            view=None
        )
        
        # Запуск дуелі
        duel_cog = interaction.client.get_cog("DuelSystem")
        if duel_cog:
            await duel_cog.execute_duel(interaction, self.challenger, self.target)

    @discord.ui.button(label="❌ Відхилити", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("❌ Це не твій дуель!", ephemeral=True)
            return

        await interaction.response.edit_message(
            content=f"❌ {self.target.mention} відхилив дуель від {self.challenger.mention}. Слабак!",
            view=None
        )

class DuelBattleView(discord.ui.View):
    def __init__(self, shooter, opponent, battle_info, duel_cog, interaction_obj):
        super().__init__(timeout=30)
        self.shooter = shooter
        self.opponent = opponent
        self.battle_info = battle_info
        self.duel_cog = duel_cog
        self.interaction_obj = interaction_obj
        self.shot_taken = False

    @discord.ui.button(label="🔫 ПОСТРІЛ!", style=discord.ButtonStyle.danger, emoji="🎯")
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.shooter or self.shot_taken:
            await interaction.response.send_message("❌ Не твоя черга стріляти!", ephemeral=True)
            return
        
        self.shot_taken = True
        await interaction.response.edit_message(view=None)
        
        # Обробити постріл
        await self.duel_cog.process_shot(
            interaction, 
            self.shooter, 
            self.opponent, 
            self.battle_info,
            first_shot=True
        )

    async def on_timeout(self):
        # Якщо гравець не стрільнув - автоматичний промах
        if not self.shot_taken:
            await self.duel_cog.process_shot(
                self.interaction_obj,
                self.shooter,
                self.opponent, 
                self.battle_info,
                first_shot=True,
                auto_miss=True
            )

class ProfileView(discord.ui.View):
    def __init__(self, user, target_user=None):
        super().__init__(timeout=300)
        self.user = user
        self.target_user = target_user or user
        self.current_page = "profile"

    async def get_profile_embed(self, interaction):
        duel_cog = interaction.client.get_cog("DuelSystem")
        stats = await duel_cog.get_user_stats(self.target_user.id, interaction.guild.id)
        rank_info = duel_cog.get_rank_info(stats['wins'])
        
        embed = discord.Embed(
            title=f"{rank_info['emoji']} Профіль гравця",
            color=0x2F3136
        )
        
        # Основна інформація
        embed.add_field(
            name="👤 Гравець", 
            value=f"**{self.target_user.display_name}**", 
            inline=True
        )
        
        embed.add_field(
            name="🏆 Ранг",
            value=f"**{rank_info['name']}**",
            inline=True
        )
        
        embed.add_field(
            name="💰 Баланс",
            value=f"**{stats['pk_balance']}** ПК",
            inline=True
        )
        
        # Статистика
        win_rate = (stats['wins'] / max(stats['wins'] + stats['losses'], 1)) * 100
        
        embed.add_field(
            name="📊 Статистика",
            value=f"```\n⚔️ Перемоги: {stats['wins']}\n💀 Поразки: {stats['losses']}\n📈 Він-рейт: {win_rate:.1f}%```",
            inline=False
        )
        
        # Опис рангу
        embed.add_field(
            name="📝 Про гравця",
            value=f"*{rank_info['description']}*",
            inline=False
        )
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.set_footer(
            text=f"Слотів інвентарю: {len(stats['items'])}/{max_slots} • Макс. ПК: 1000"
        )
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        
        return embed

    async def get_inventory_embed(self, interaction):
        duel_cog = interaction.client.get_cog("DuelSystem")
        stats = await duel_cog.get_user_stats(self.target_user.id, interaction.guild.id)
        
        embed = discord.Embed(
            title=f"🎒 Інвентар {self.target_user.display_name}",
            color=0x7289DA
        )
        
        if not stats['items']:
            embed.description = "```\n📦 Інвентар порожній\n\n💡 Купіть предмети в магазині!```"
        else:
            items_text = "```\n"
            for i, item_id in enumerate(stats['items'], 1):
                if item_id in SHOP_ITEMS:
                    item = SHOP_ITEMS[item_id]
                    items_text += f"{i}. {item['name']}\n"
                    items_text += f"   ✅ {item['buff']}\n"
                    items_text += f"   ❌ {item['debuff']}\n\n"
            items_text += "```"
            embed.description = items_text
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.set_footer(text=f"Використано слотів: {len(stats['items'])}/{max_slots}")
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        
        return embed

    async def get_shop_embed(self, interaction):
        duel_cog = interaction.client.get_cog("DuelSystem")
        stats = await duel_cog.get_user_stats(self.user.id, interaction.guild.id)
        
        embed = discord.Embed(
            title="🛍️ МАГАЗИН ПРЕДМЕТІВ",
            description=f"💰 **Ваш баланс: {stats['pk_balance']} ПК**",
            color=0xF1C40F
        )
        
        shop_text = "```\n"
        for item_id, item in SHOP_ITEMS.items():
            status = "✅" if stats['pk_balance'] >= item['price'] else "❌"
            shop_text += f"{status} {item['name']} - {item['price']} ПК\n"
            shop_text += f"   💚 {item['buff']}\n"
            shop_text += f"   💔 {item['debuff']}\n\n"
        shop_text += "```"
        
        embed.description += f"\n{shop_text}"
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.set_footer(text=f"Слотів інвентарю: {len(stats['items'])}/{max_slots}")
        
        return embed

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

        inventory_btn = discord.ui.Button(
            label="🎒 Інвентар", 
            style=discord.ButtonStyle.primary if self.current_page == "inventory" else discord.ButtonStyle.secondary,
            disabled=self.current_page == "inventory"
        )
        inventory_btn.callback = self.show_inventory
        self.add_item(inventory_btn)

        # Магазин тільки для власного профілю
        if self.target_user == self.user:
            shop_btn = discord.ui.Button(
                label="🛍️ Магазин",
                style=discord.ButtonStyle.primary if self.current_page == "shop" else discord.ButtonStyle.secondary,
                disabled=self.current_page == "shop"
            )
            shop_btn.callback = self.show_shop
            self.add_item(shop_btn)

        # Кнопки покупки для магазину
        if self.current_page == "shop" and self.target_user == self.user:
            for i, (item_id, item) in enumerate(SHOP_ITEMS.items()):
                row = 1 + (i // 5)  # 5 кнопок на ряд
                btn = discord.ui.Button(
                    label=f"{item['name']} ({item['price']} ПК)",
                    custom_id=f"buy_{item_id}",
                    style=discord.ButtonStyle.success,
                    row=row
                )
                btn.callback = self.create_buy_callback(item_id)
                self.add_item(btn)

    def create_buy_callback(self, item_id):
        async def buy_callback(interaction):
            if interaction.user != self.user:
                await interaction.response.send_message("❌ Це не ваш магазин!", ephemeral=True)
                return

            duel_cog = interaction.client.get_cog("DuelSystem")
            if duel_cog:
                success = await duel_cog.buy_item_inline(interaction, item_id)
                if success:
                    embed = await self.get_shop_embed(interaction)
                    await self.update_view(interaction)
                    await interaction.edit_original_response(embed=embed, view=self)
        
        return buy_callback

    async def show_profile(self, interaction):
        self.current_page = "profile"
        embed = await self.get_profile_embed(interaction)
        await self.update_view(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_inventory(self, interaction):
        self.current_page = "inventory"
        embed = await self.get_inventory_embed(interaction)
        await self.update_view(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_shop(self, interaction):
        if self.target_user != self.user:
            await interaction.response.send_message("❌ Магазин доступний тільки у власному профілі!", ephemeral=True)
            return
            
        self.current_page = "shop"
        embed = await self.get_shop_embed(interaction)
        await self.update_view(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

class DuelSystem(commands.Cog):
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
                        title="💥 DDoS АТАКА!",
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
            description=f"🎯 **{first_shooter.mention}** стріляє першим!",
            color=0xE74C3C
        )
        
        battle_embed.add_field(
            name=f"{self.get_rank_info(challenger_stats['wins'])['emoji']} Челленджер",
            value=f"**{challenger.display_name}**\nПеремоги: {challenger_stats['wins']}",
            inline=True
        )
        
        battle_embed.add_field(
            name="🆚", 
            value="**VS**", 
            inline=True
        )
        
        battle_embed.add_field(
            name=f"{self.get_rank_info(target_stats['wins'])['emoji']} Опонент",
            value=f"**{target.display_name}**\nПеремоги: {target_stats['wins']}",
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
                result_text = f"🏛️ **Модератор втрутився!** {winner.mention} переміг!"
            else:
                result_text = f"🎯 **{winner.mention}** влучно стріляє! Переможець визначений!"
            
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
            value=f"**{winner.mention}**\n+{pk_gained} ПК\n💰 Баланс: {new_winner_balance} ПК",
            inline=True
        )
        
        result_embed.add_field(
            name="💀 Переможений",
            value=f"**{loser.mention}**\n-{pk_lost} ПК\n💰 Баланс: {new_loser_balance} ПК",
            inline=True
        )
        
        meme_comments = [
            "Епічна битва віків!",
            "Це було неочікувано!",
            "Хтось викликає швидку?", 
            "Мама, я в телевізорі!",
            "Красиво зіграв!",
            "Чекай реванш!"
        ]
        
        result_embed.set_footer(text=random.choice(meme_comments))
        
        await interaction.edit_original_response(embed=result_embed, view=None)

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
            description=f"{challenger.mention} викликає {target.mention} на дуель!",
            color=0xE67E22
        )
        
        embed.add_field(
            name=f"{challenger_rank['emoji']} Челленджер",
            value=f"**{challenger.display_name}**\n{challenger_rank['name']}\nПеремоги: {challenger_stats['wins']}",
            inline=True
        )
        
        embed.add_field(
            name=f"{target_rank['emoji']} Опонент", 
            value=f"**{target.display_name}**\n{target_rank['name']}\nПеремоги: {target_stats['wins']}",
            inline=True
        )
        
        embed.set_footer(text="У опонента є 60 секунд щоб відповісти!")
        
        await interaction.response.send_message(
            content=f"{target.mention}, тебе викликають на дуель!",
            embed=embed,
            view=view
        )

    @app_commands.command(name="pidor_profile", description="Показати профіль гравця з інвентарем та магазином")
    @app_commands.describe(user="Чий профіль показати (за замовчуванням - свій)")
    async def pidor_profile_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target_user = user or interaction.user
        
        view = ProfileView(interaction.user, target_user)
        embed = await view.get_profile_embed(interaction)
        await view.update_view(interaction)
        
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

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
        
        embed = discord.Embed(
            title="📈 СТАТИСТИКА ДУЕЛЕЙ СЕРВЕРА",
            color=0x3498DB
        )
        
        embed.add_field(
            name="🎯 Загальна статистика",
            value=f"```\n⚔️ Всього дуелей: {total_duels}\n👥 Активних гравців: {total_players}```",
            inline=False
        )
        
        if most_active:
            try:
                user = interaction.guild.get_member(int(most_active['user_id']))
                if user:
                    rank_info = self.get_rank_info(most_active['wins'])
                    embed.add_field(
                        name="👑 Найактивніший гравець",
                        value=f"```\n{user.display_name} {rank_info['emoji']}\n⚔️ Перемоги: {most_active['wins']}\n💀 Поразки: {most_active['losses']}\n💰 ПК: {most_active['pk_balance']}```",
                        inline=True
                    )
            except:
                pass
        
        # Останні дуелі
        recent_duels = await db.duel_history.find(
            {"guild_id": interaction.guild.id}
        ).sort("timestamp", -1).limit(5).to_list(length=5)
        
        if recent_duels:
            recent_lines = ["🕐 ОСТАННІ ДУЕЛІ\n"]
            for duel in recent_duels:
                try:
                    winner = interaction.guild.get_member(int(duel['winner']))
                    loser = interaction.guild.get_member(int(duel['loser']))
                    if winner and loser:
                        recent_lines.append(f"• {winner.display_name} > {loser.display_name}")
                except:
                    continue
            
            if len(recent_lines) > 1:
                embed.add_field(
                    name="⏰ Нещодавні бої",
                    value="```\n" + "\n".join(recent_lines) + "```",
                    inline=False
                )
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DuelSystem(bot))