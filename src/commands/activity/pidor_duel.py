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

class ProfileView(discord.ui.View):
    def __init__(self, user, target_user=None):
        super().__init__(timeout=300)
        self.user = user
        self.target_user = target_user or user
        self.current_page = "profile"  # profile, inventory, shop

    async def get_profile_embed(self, interaction):
        duel_cog = interaction.client.get_cog("DuelSystem")
        stats = await duel_cog.get_user_stats(self.target_user.id, interaction.guild.id)
        rank_info = duel_cog.get_rank_info(stats['wins'])
        
        embed = discord.Embed(
            title=f"{rank_info['emoji']} Профіль {self.target_user.display_name}",
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🏆 Ранг",
            value=f"**{rank_info['name']}**\n*{rank_info['description']}*",
            inline=False
        )
        
        win_rate = (stats['wins'] / max(stats['wins'] + stats['losses'], 1)) * 100
        
        embed.add_field(
            name="📊 Статистика",
            value=f"Перемоги: **{stats['wins']}**\nПоразки: **{stats['losses']}**\nВін-рейт: **{win_rate:.1f}%**",
            inline=True
        )
        
        embed.add_field(
            name="💰 Баланс",
            value=f"**{stats['pk_balance']}** ПК\n(макс. 1000)",
            inline=True
        )
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.add_field(
            name=f"🎒 Інвентар ({len(stats['items'])}/{max_slots})",
            value=f"Предметів: {len(stats['items'])}\n*(натисни кнопку щоб переглянути)*",
            inline=True
        )
        
        embed.set_thumbnail(url=self.target_user.display_avatar.url)
        return embed

    async def get_inventory_embed(self, interaction):
        duel_cog = interaction.client.get_cog("DuelSystem")
        stats = await duel_cog.get_user_stats(self.target_user.id, interaction.guild.id)
        
        embed = discord.Embed(
            title=f"🎒 Інвентар {self.target_user.display_name}",
            color=discord.Color.purple()
        )
        
        if not stats['items']:
            embed.description = "Інвентар порожній."
            if self.target_user == self.user:
                embed.description += " Купіть предмети в магазині!"
        else:
            items_text = ""
            for i, item_id in enumerate(stats['items'], 1):
                if item_id in SHOP_ITEMS:
                    item = SHOP_ITEMS[item_id]
                    items_text += f"**{i}.** {item['name']}\n"
                    items_text += f"   ✅ {item['buff']}\n"
                    items_text += f"   ❌ {item['debuff']}\n\n"
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
            description=f"Ваш баланс: **{stats['pk_balance']} ПК**",
            color=discord.Color.gold()
        )
        
        shop_text = ""
        for item_id, item in SHOP_ITEMS.items():
            affordable = "✅" if stats['pk_balance'] >= item['price'] else "❌"
            shop_text += f"{affordable} **{item['name']}** - {item['price']} ПК\n"
            shop_text += f"   ✅ {item['buff']}\n"
            shop_text += f"   ❌ {item['debuff']}\n\n"
        
        embed.description += f"\n\n{shop_text}"
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.set_footer(text=f"Слотів інвентарю: {len(stats['items'])}/{max_slots}")
        return embed

    async def update_view(self, interaction):
        self.clear_items()
        
        # Кнопки навігації (завжди показуємо)
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
            # Додаємо кнопки покупки у другому ряді
            item_buttons = []
            for item_id, item in list(SHOP_ITEMS.items())[:5]:  # Перші 5 предметів
                btn = discord.ui.Button(
                    label=f"{item['name']} ({item['price']} ПК)",
                    custom_id=f"buy_{item_id}",
                    style=discord.ButtonStyle.success,
                    row=1
                )
                btn.callback = self.create_buy_callback(item_id)
                self.add_item(btn)
            
            # Останній предмет в третьому ряді
            if len(SHOP_ITEMS) > 5:
                for item_id, item in list(SHOP_ITEMS.items())[5:]:
                    btn = discord.ui.Button(
                        label=f"{item['name']} ({item['price']} ПК)",
                        custom_id=f"buy_{item_id}",
                        style=discord.ButtonStyle.success,
                        row=2
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
                    # Оновити вигляд після покупки
                    embed = await self.get_shop_embed(interaction)
                    await self.update_view(interaction)
                    await interaction.edit_original_response(embed=embed, view=self)
        
        return buy_callback

    async def show_profile(self, interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Це не ваш профіль!", ephemeral=True)
            return
            
        self.current_page = "profile"
        embed = await self.get_profile_embed(interaction)
        await self.update_view(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_inventory(self, interaction):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Це не ваш профіль!", ephemeral=True)
            return
            
        self.current_page = "inventory"
        embed = await self.get_inventory_embed(interaction)
        await self.update_view(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

    async def show_shop(self, interaction):
        if interaction.user != self.user or self.target_user != self.user:
            await interaction.response.send_message("❌ Магазин доступний тільки у власному профілі!", ephemeral=True)
            return
            
        self.current_page = "shop"
        embed = await self.get_shop_embed(interaction)
        await self.update_view(interaction)
        await interaction.response.edit_message(embed=embed, view=self)

class DuelSystem(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {}  # user_id: last_duel_time
        self.daily_limits = {}  # user_id: {date: earned_pk}

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
            # Новий день - скидаємо ліміт
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
            await interaction.edit_original_response(
                content=f"🎲 **Випадкова подія:** {random_event['name']}\n{random_event['description']}\n\nПідготовка до бою..."
            )
            await asyncio.sleep(3)
            
            # Обробити ефекти події
            if random_event["name"] == "DDoS атака":
                await interaction.edit_original_response(
                    content="💥 **DDoS атака!** Дуель повторюється через 10 секунд..."
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

        # Рандомна задишка
        luck_bonus = random.choice([challenger, target])
        
        # Початок дуелі
        embed = discord.Embed(
            title="⚔️ ДУЕЛЬ РОЗПОЧАТО!",
            color=discord.Color.red()
        )
        embed.add_field(
            name=f"{self.get_rank_info(challenger_stats['wins'])['emoji']} {challenger.display_name}",
            value=f"Перемоги: {challenger_stats['wins']}\nПК: {challenger_stats['pk_balance']}",
            inline=True
        )
        embed.add_field(
            name="🆚",
            value="VS",
            inline=True
        )
        embed.add_field(
            name=f"{self.get_rank_info(target_stats['wins'])['emoji']} {target.display_name}",
            value=f"Перемоги: {target_stats['wins']}\nПК: {target_stats['pk_balance']}",
            inline=True
        )
        
        if random_event:
            embed.add_field(
                name="🎲 Випадкова подія",
                value=f"**{random_event['name']}**\n{random_event['description']}",
                inline=False
            )
        
        embed.add_field(
            name="🍀 Рандомна задишка",
            value=f"{luck_bonus.mention} отримує +10% до шансу перемоги!",
            inline=False
        )
        
        await interaction.edit_original_response(content=None, embed=embed)
        await asyncio.sleep(3)

        # Визначити переможця
        winner = None
        loser = None
        
        if event_effects.get("random_winner"):
            # Випадковий переможець через втручання модератора
            winner, loser = random.choice([(challenger, target), (target, challenger)])
            battle_text = "🏛️ **Модератор втрутився!** Переможець визначений випадково!"
        
        else:
            # Нормальна дуель з розрахунком шансів
            challenger_accuracy = 50
            target_accuracy = 50
            
            # Застосувати ефекти подій
            if "accuracy_boost" in event_effects:
                for user_id, boost in event_effects["accuracy_boost"].items():
                    if user_id == challenger.id:
                        challenger_accuracy += boost
                    elif user_id == target.id:
                        target_accuracy += boost
            
            if "accuracy_penalty" in event_effects:
                for user_id, penalty in event_effects["accuracy_penalty"].items():
                    if user_id == challenger.id:
                        challenger_accuracy -= penalty
                    elif user_id == target.id:
                        target_accuracy -= penalty
            
            # Задишка
            if luck_bonus == challenger:
                challenger_accuracy += 10
            else:
                target_accuracy += 10
            
            # Визначити черговість пострілів
            first_shooter = random.choice([challenger, target])
            second_shooter = target if first_shooter == challenger else challenger
            
            first_accuracy = challenger_accuracy if first_shooter == challenger else target_accuracy
            second_accuracy = target_accuracy if first_shooter == challenger else challenger_accuracy
            
            # Перший постріл
            if random.random() * 100 < first_accuracy:
                winner = first_shooter
                loser = second_shooter
                battle_text = f"🎯 **{first_shooter.mention}** влучно стріляє першим!"
            else:
                # Другий постріл
                if random.random() * 100 < second_accuracy:
                    winner = second_shooter
                    loser = first_shooter
                    battle_text = f"💥 **{first_shooter.mention}** промахнувся! **{second_shooter.mention}** не дав другого шансу!"
                else:
                    # Обидва промахнулися - випадковий переможець
                    winner, loser = random.choice([(challenger, target), (target, challenger)])
                    battle_text = f"😅 **Обидва промахнулися!** Але **{winner.mention}** виявився спритнішим!"

        # Розрахунок ПК
        winner_stats = await self.get_user_stats(winner.id, guild_id)
        loser_stats = await self.get_user_stats(loser.id, guild_id)
        
        winner_rank = self.get_rank_info(winner_stats['wins'])
        loser_rank = self.get_rank_info(loser_stats['wins'])
        
        pk_gained = winner_rank['win_reward']
        pk_lost = loser_rank['loss_penalty']
        
        # Перевірити щоденний ліміт
        winner_can_earn = await self.check_daily_limit(winner.id, guild_id)
        if not winner_can_earn:
            pk_gained = 0

        # Оновити статистику
        new_winner_balance = min(winner_stats['pk_balance'] + pk_gained, 1000)
        new_loser_balance = max(loser_stats['pk_balance'] - pk_lost, 0)
        
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
        
        # Зберегти історію дуелі
        await db.duel_history.insert_one({
            "guild_id": guild_id,
            "winner": str(winner.id),
            "loser": str(loser.id),
            "pk_change": {"winner": pk_gained, "loser": pk_lost},
            "event": random_event["name"] if random_event else None,
            "timestamp": datetime.utcnow()
        })
        
        # Оновити кулдауни
        self.cooldowns[challenger.id] = datetime.now()
        self.cooldowns[target.id] = datetime.now()

        # Результат дуелі
        result_embed = discord.Embed(
            title="🏆 РЕЗУЛЬТАТ ДУЕЛІ",
            description=battle_text,
            color=discord.Color.green()
        )
        
        result_embed.add_field(
            name="🥇 Переможець",
            value=f"**{winner.mention}**\n+{pk_gained} ПК (Баланс: {new_winner_balance})",
            inline=True
        )
        
        result_embed.add_field(
            name="💀 Переможений",
            value=f"**{loser.mention}**\n-{pk_lost} ПК (Баланс: {new_loser_balance})",
            inline=True
        )
        
        # Мемні коментарі
        meme_comments = [
            "Епічна битва віків!",
            "Це було неочікувано!",
            "Хтось викликає швидку?",
            "Мама, я в телевізорі!",
            "Красиво зіграв!",
            "Чекай реванш!"
        ]
        
        result_embed.set_footer(text=random.choice(meme_comments))
        
        await interaction.edit_original_response(content=None, embed=result_embed)

    async def buy_item_inline(self, interaction, item_id: str):
        """Купити предмет в магазині (для inline використання)"""
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
            color=discord.Color.orange()
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

    @app_commands.command(name="pidor_shop", description="Відкрити магазин предметів")
    async def pidor_shop_command(self, interaction: discord.Interaction):
        stats = await self.get_user_stats(interaction.user.id, interaction.guild.id)
        
        embed = discord.Embed(
            title="🛍️ МАГАЗИН ПРЕДМЕТІВ",
            description=f"Ваш баланс: **{stats['pk_balance']} ПК**",
            color=discord.Color.gold()
        )
        
        for item_id, item in SHOP_ITEMS.items():
            embed.add_field(
                name=f"{item['name']} - {item['price']} ПК",
                value=f"✅ {item['buff']}\n❌ {item['debuff']}",
                inline=True
            )
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.set_footer(text=f"Слотів інвентарю: {len(stats['items'])}/{max_slots}")
        
        view = ShopView(interaction.user)
        await interaction.response.send_message(embed=embed, view=view, ephemeral=True)

    @app_commands.command(name="pidor_leaderboard", description="Показати таблицю лідерів")
    async def pidor_leaderboard_command(self, interaction: discord.Interaction):
        # Отримати топ-10 гравців
        top_players = await db.duel_stats.find(
            {"guild_id": interaction.guild.id}
        ).sort("wins", -1).limit(10).to_list(length=10)
        
        if not top_players:
            await interaction.response.send_message(
                "📊 Ще ніхто не проводив дуелей на цьому сервері!",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🏆 ТАБЛИЦЯ ЛІДЕРІВ",
            color=discord.Color.gold()
        )
        
        medals = ["🥇", "🥈", "🥉"] + ["🏅"] * 7
        
        leaderboard_text = ""
        for i, player_stats in enumerate(top_players):
            try:
                user = interaction.guild.get_member(int(player_stats['user_id']))
                if user:
                    rank_info = self.get_rank_info(player_stats['wins'])
                    win_rate = (player_stats['wins'] / max(player_stats['wins'] + player_stats['losses'], 1)) * 100
                    
                    leaderboard_text += (
                        f"{medals[i]} **{user.display_name}** {rank_info['emoji']}\n"
                        f"   Перемоги: {player_stats['wins']} | "
                        f"Він-рейт: {win_rate:.1f}% | "
                        f"ПК: {player_stats['pk_balance']}\n\n"
                    )
            except (ValueError, AttributeError):
                continue
        
        embed.description = leaderboard_text or "Немає активних гравців"
        
        await interaction.response.send_message(embed=embed)

        # Додамо команду для перегляду інвентарю
        
    @app_commands.command(name="pidor_inventory", description="Показати свій інвентар предметів")
    async def pidor_inventory_command(self, interaction: discord.Interaction):
        stats = await self.get_user_stats(interaction.user.id, interaction.guild.id)
        
        embed = discord.Embed(
            title="🎒 ВАШ ІНВЕНТАР",
            color=discord.Color.purple()
        )
        
        if not stats['items']:
            embed.description = "Ваш інвентар порожній. Купіть предмети в `/pidor_shop`!"
        else:
            items_text = ""
            for i, item_id in enumerate(stats['items'], 1):
                item = SHOP_ITEMS[item_id]
                items_text += f"**{i}.** {item['name']}\n"
                items_text += f"   ✅ {item['buff']}\n"
                items_text += f"   ❌ {item['debuff']}\n\n"
            embed.description = items_text
        
        max_slots = 1 + (stats['wins'] // 10)
        embed.set_footer(text=f"Використано слотів: {len(stats['items'])}/{max_slots}")
        
        await interaction.response.send_message(embed=embed, ephemeral=True)
    
    @app_commands.command(name="pidor_stats", description="Показати статистику дуелей сервера")
    async def pidor_stats_command(self, interaction: discord.Interaction):
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
            color=discord.Color.blue()
        )
        
        embed.add_field(
            name="🎯 Загальна статистика",
            value=f"Всього дуелей: **{total_duels}**\nАктивних гравців: **{total_players}**",
            inline=False
        )
        
        if most_active:
            try:
                user = interaction.guild.get_member(int(most_active['user_id']))
                if user:
                    rank_info = self.get_rank_info(most_active['wins'])
                    embed.add_field(
                        name="👑 Найактивніший гравець",
                        value=f"**{user.display_name}** {rank_info['emoji']}\n"
                              f"Перемоги: {most_active['wins']}\n"
                              f"Поразки: {most_active['losses']}",
                        inline=True
                    )
            except:
                pass
        
        # Останні дуелі
        recent_duels = await db.duel_history.find(
            {"guild_id": interaction.guild.id}
        ).sort("timestamp", -1).limit(5).to_list(length=5)
        
        if recent_duels:
            recent_text = ""
            for duel in recent_duels:
                try:
                    winner = interaction.guild.get_member(int(duel['winner']))
                    loser = interaction.guild.get_member(int(duel['loser']))
                    if winner and loser:
                        recent_text += f"• **{winner.display_name}** переміг **{loser.display_name}**\n"
                except:
                    continue
            
            if recent_text:
                embed.add_field(
                    name="🕐 Останні 5 дуелей",
                    value=recent_text,
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(DuelSystem(bot))