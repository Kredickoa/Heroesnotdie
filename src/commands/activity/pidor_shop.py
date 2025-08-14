import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict
from modules.db import get_database
from ._constants import SHOP_ITEMS, RANKS

db = get_database()

class ShopCommand(commands.Cog):
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

    async def buy_item(self, user_id: int, guild_id: int, item_id: str) -> tuple[bool, str]:
        """Купити предмет"""
        if item_id not in SHOP_ITEMS:
            return False, "❌ Невідомий предмет!"
        
        stats = await self.get_user_stats(user_id, guild_id)
        item = SHOP_ITEMS[item_id]
        
        # Перевірити баланс
        if stats['pk_balance'] < item['price']:
            return False, f"❌ Недостатньо ПК! Потрібно {item['price']} ПК, а у вас {stats['pk_balance']} ПК."
        
        # Перевірити слоти інвентарю
        max_slots = 1 + (stats['wins'] // 10)
        if len(stats['items']) >= max_slots:
            return False, f"❌ Інвентар заповнений! Доступно слотів: {max_slots}"
        
        # Перевірити чи вже є цей предмет
        if item_id in stats['items']:
            return False, f"❌ У вас вже є **{item['name']}**!"
        
        # Купити предмет
        new_balance = stats['pk_balance'] - item['price']
        new_items = stats['items'] + [item_id]
        
        await db.duel_stats.update_one(
            {"user_id": str(user_id), "guild_id": guild_id},
            {
                "$set": {
                    "pk_balance": new_balance,
                    "items": new_items
                }
            }
        )
        
        return True, f"✅ Куплено **{item['name']}** за {item['price']} ПК!\n<:bank:1405489965244088340> Новий баланс: {new_balance} ПК"

    class ShopView(discord.ui.View):
        def __init__(self, user, target_user, shop_cog):
            super().__init__(timeout=300)
            self.user = user
            self.target_user = target_user
            self.shop_cog = shop_cog
            self.current_mode = "inventory"  # inventory або shop
            self.current_page = 0
            self.items_per_page = 5

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            """Перевірює чи користувач може використовувати інтерфейс"""
            if interaction.user != self.user:
                await interaction.response.send_message("❌ Це не твій інтерфейс!", ephemeral=True)
                return False
            return True

        async def get_inventory_embed(self, interaction):
            """Створити embed для інвентарю"""
            stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
            
            embed = discord.Embed(
                title="🎒 ІНВЕНТАР",
                color=0x7c7cf0
            )
            
            embed.set_author(
                name=f"{self.target_user.display_name}",
                icon_url=self.target_user.display_avatar.url
            )
            
            max_slots = 1 + (stats['wins'] // 10)
            total_value = sum(SHOP_ITEMS.get(item_id, {}).get('price', 0) for item_id in stats.get('items', []))
            
            # Статистика користувача
            stats_text = f"""
┌─ <:bank:1405489965244088340> **ВАШІ РЕСУРСИ** ─┐
│ **Баланс:** `{stats['pk_balance']} ПК`
│ **Слотів зайнято:** `{len(stats.get('items', []))}/{max_slots}`
│ **Загальна вартість предметів:** `{total_value} ПК`
│ <:trophy:1405488585372860517> **Перемог:** `{stats['wins']}` • **Поразок:** `{stats['losses']}`
└─────────────────────────────────┘
            """
            embed.add_field(name="　", value=stats_text, inline=False)
            
            if not stats.get('items'):
                empty_inventory = f"""
┌─ 📦 **ВАШІ ПРЕДМЕТИ** ─┐
│
│ `Інвентар порожній`
│
│ 💡 Натисніть кнопку '<:market:1405145855178182736> Магазин' щоб
│    придбати предмети для дуелей!
│
└──────────────────────────┘
                """
                embed.add_field(name="　", value=empty_inventory, inline=False)
            else:
                # Розраховувати пагінацію
                items = stats['items']
                total_pages = (len(items) - 1) // self.items_per_page + 1
                start_idx = self.current_page * self.items_per_page
                end_idx = min(start_idx + self.items_per_page, len(items))
                page_items = items[start_idx:end_idx]
                
                # Показати предмети на поточній сторінці
                items_text = "┌─ 📦 **ВАШІ ПРЕДМЕТИ** ─┐\n"
                
                for i, item_id in enumerate(page_items):
                    item_number = start_idx + i + 1
                    if item_id in SHOP_ITEMS:
                        item = SHOP_ITEMS[item_id]
                        items_text += f"│ `{item_number}.` **{item['name']}** `({item['price']} ПК)`\n"
                        items_text += f"│ ┣━ ✅ {item['buff']}\n"
                        items_text += f"│ ┗━ ❌ {item['debuff']}\n│\n"
                    else:
                        items_text += f"│ `{item_number}.` **Невідомий предмет**\n│\n"
                
                items_text += "└──────────────────────────┘"
                
                field_name = "　"
                if total_pages > 1:
                    field_name = f"📄 Сторінка {self.current_page + 1}/{total_pages}"
                
                embed.add_field(name=field_name, value=items_text, inline=False)
            
            return embed

        async def get_shop_embed(self, interaction):
            """Створити embed для магазину"""
            stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
            
            embed = discord.Embed(
                title="🛍️ МАГАЗИН ПРЕДМЕТІВ",
                color=0x7c7cf0
            )
            
            embed.set_author(
                name=f"{self.target_user.display_name}",
                icon_url=self.target_user.display_avatar.url
            )
            
            max_slots = 1 + (stats['wins'] // 10)
            
            # Інформація про баланс та слоти
            balance_text = f"""
┌─ <:bank:1405489965244088340> **ВАШІ РЕСУРСИ** ─┐
│ **Ваш баланс:** `{stats['pk_balance']} ПК`
│ **Вільних слотів:** `{max_slots - len(stats['items'])}/{max_slots}`
│ **Всього предметів у магазині:** `{len(SHOP_ITEMS)}`
└─────────────────────────────────────┘
            """
            embed.add_field(name="　", value=balance_text, inline=False)
            
            # Показати предмети магазину
            items = list(SHOP_ITEMS.items())
            total_pages = (len(items) - 1) // self.items_per_page + 1
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, len(items))
            page_items = items[start_idx:end_idx]
            
            shop_text = "┌─ <:market:1405145855178182736> **АСОРТИМЕНТ** ─┐\n"
            
            for i, (item_id, item) in enumerate(page_items):
                item_number = start_idx + i + 1
                
                # Визначити статус предмета
                can_afford = stats['pk_balance'] >= item['price']
                has_space = len(stats['items']) < max_slots
                already_owns = item_id in stats['items']
                
                if already_owns:
                    status = "✅ КУПЛЕНО"
                    status_emoji = "✅"
                elif can_afford and has_space:
                    status = "🟢 ДОСТУПНО"
                    status_emoji = "🛒"
                else:
                    status = "🔴 НЕДОСТУПНО"
                    status_emoji = "❌"
                
                shop_text += f"│ `{item_number}.` {status_emoji} **{item['name']}** - `{item['price']} ПК` [{status}]\n"
                shop_text += f"│ ┣━ ✅ {item['buff']}\n"
                shop_text += f"│ ┗━ ❌ {item['debuff']}\n│\n"
            
            shop_text += "└─────────────────────────────────────────┘"
            
            field_name = "　"
            if total_pages > 1:
                field_name = f"📄 Сторінка {self.current_page + 1}/{total_pages}"
            
            embed.add_field(name=field_name, value=shop_text, inline=False)
            
            return embed

        async def update_view(self, interaction):
            """Оновити кнопки інтерфейсу"""
            self.clear_items()
            
            # Основні кнопки навігації
            if self.current_mode == "inventory":
                # Кнопка переходу в магазин (тільки для власника)
                if self.target_user == self.user:
                    shop_btn = discord.ui.Button(
                        label="Магазин",
                        emoji="<:market:1405145855178182736>",
                        style=discord.ButtonStyle.primary,
                        custom_id="switch_to_shop"
                    )
                    shop_btn.callback = self.switch_to_shop
                    self.add_item(shop_btn)
                
                # Пагінація для інвентарю
                stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
                items = stats.get('items', [])
                if items:
                    total_pages = (len(items) - 1) // self.items_per_page + 1
                    if total_pages > 1:
                        if self.current_page > 0:
                            prev_btn = discord.ui.Button(
                                emoji="◀️",
                                style=discord.ButtonStyle.secondary,
                                custom_id="prev_page"
                            )
                            prev_btn.callback = self.previous_page
                            self.add_item(prev_btn)
                        
                        if self.current_page < total_pages - 1:
                            next_btn = discord.ui.Button(
                                emoji="▶️",
                                style=discord.ButtonStyle.secondary,
                                custom_id="next_page"
                            )
                            next_btn.callback = self.next_page
                            self.add_item(next_btn)
            
            else:  # shop mode
                # Кнопка повернення в інвентар
                inventory_btn = discord.ui.Button(
                    label="Інвентар",
                    emoji="🎒",
                    style=discord.ButtonStyle.secondary,
                    custom_id="switch_to_inventory"
                )
                inventory_btn.callback = self.switch_to_inventory
                self.add_item(inventory_btn)
                
                # Пагінація для магазину
                items = list(SHOP_ITEMS.items())
                total_pages = (len(items) - 1) // self.items_per_page + 1
                
                if total_pages > 1:
                    if self.current_page > 0:
                        prev_btn = discord.ui.Button(
                            emoji="◀️",
                            style=discord.ButtonStyle.secondary,
                            custom_id="prev_page"
                        )
                        prev_btn.callback = self.previous_page
                        self.add_item(prev_btn)
                    
                    if self.current_page < total_pages - 1:
                        next_btn = discord.ui.Button(
                            emoji="▶️",
                            style=discord.ButtonStyle.secondary,
                            custom_id="next_page"
                        )
                        next_btn.callback = self.next_page
                        self.add_item(next_btn)
                
                # Кнопки покупки (тільки для власника)
                if self.target_user == self.user:
                    stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
                    items = list(SHOP_ITEMS.items())
                    start_idx = self.current_page * self.items_per_page
                    end_idx = min(start_idx + self.items_per_page, len(items))
                    page_items = items[start_idx:end_idx]
                    
                    # Додаємо кнопки покупки для кожного предмета
                    for item_id, item in page_items:
                        can_afford = stats['pk_balance'] >= item['price']
                        has_space = len(stats['items']) < (1 + (stats['wins'] // 10))
                        already_owns = item_id in stats['items']
                        
                        if already_owns:
                            btn_style = discord.ButtonStyle.success
                            btn_label = f"✅ {item['name']}"
                            btn_disabled = True
                        elif can_afford and has_space:
                            btn_style = discord.ButtonStyle.primary
                            btn_label = f"🛒 {item['name']} ({item['price']} ПК)"
                            btn_disabled = False
                        else:
                            btn_style = discord.ButtonStyle.danger
                            btn_label = f"❌ {item['name']} ({item['price']} ПК)"
                            btn_disabled = True
                        
                        buy_btn = discord.ui.Button(
                            label=btn_label,
                            style=btn_style,
                            disabled=btn_disabled,
                            custom_id=f"buy_{item_id}"
                        )
                        buy_btn.callback = self.create_buy_callback(item_id)
                        self.add_item(buy_btn)
            
            # Кнопка оновлення
            refresh_btn = discord.ui.Button(
                emoji="🔄",
                style=discord.ButtonStyle.secondary,
                custom_id="refresh"
            )
            refresh_btn.callback = self.refresh
            self.add_item(refresh_btn)

        def create_buy_callback(self, item_id):
            async def buy_callback(interaction):
                success, message = await self.shop_cog.buy_item(
                    self.target_user.id, 
                    interaction.guild.id, 
                    item_id
                )
                
                if success:
                    embed = await self.get_shop_embed(interaction)
                    await self.update_view(interaction)
                    await interaction.response.edit_message(embed=embed, view=self)
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            
            return buy_callback

        async def switch_to_shop(self, interaction):
            """Перемикнути на магазин"""
            self.current_mode = "shop"
            self.current_page = 0
            embed = await self.get_shop_embed(interaction)
            await self.update_view(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

        async def switch_to_inventory(self, interaction):
            """Перемикнути на інвентар"""
            self.current_mode = "inventory"
            self.current_page = 0
            embed = await self.get_inventory_embed(interaction)
            await self.update_view(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

        async def previous_page(self, interaction):
            """Попередня сторінка"""
            if self.current_page > 0:
                self.current_page -= 1
                if self.current_mode == "inventory":
                    embed = await self.get_inventory_embed(interaction)
                else:
                    embed = await self.get_shop_embed(interaction)
                await self.update_view(interaction)
                await interaction.response.edit_message(embed=embed, view=self)

        async def next_page(self, interaction):
            """Наступна сторінка"""
            if self.current_mode == "inventory":
                stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
                items = stats.get('items', [])
                total_pages = (len(items) - 1) // self.items_per_page + 1 if items else 1
            else:
                items = list(SHOP_ITEMS.items())
                total_pages = (len(items) - 1) // self.items_per_page + 1
            
            if self.current_page < total_pages - 1:
                self.current_page += 1
                if self.current_mode == "inventory":
                    embed = await self.get_inventory_embed(interaction)
                else:
                    embed = await self.get_shop_embed(interaction)
                await self.update_view(interaction)
                await interaction.response.edit_message(embed=embed, view=self)

        async def refresh(self, interaction):
            """Оновити поточний режим"""
            if self.current_mode == "inventory":
                embed = await self.get_inventory_embed(interaction)
            else:
                embed = await self.get_shop_embed(interaction)
            await self.update_view(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

    @app_commands.command(name="pidor_shop", description="Переглянути інвентар та магазин предметів")
    @app_commands.describe(user="Чий профіль переглянути (за замовчуванням - свій)")
    async def pidor_shop_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        
        target_user = user or interaction.user
        
        # Перевірити чи це бот
        if target_user.bot:
            await interaction.followup.send(
                "🤖 Боти не мають інвентарів. Вони зберігають все в хмарі!",
                ephemeral=True
            )
            return
        
        view = self.ShopView(interaction.user, target_user, self)
        embed = await view.get_inventory_embed(interaction)
        await view.update_view(interaction)
        
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ShopCommand(bot))