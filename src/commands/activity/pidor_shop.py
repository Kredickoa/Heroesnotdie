import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict
from modules.db import get_database
from ._constants import SHOP_ITEMS, RANKS

db = get_database()

class ShopInventoryCommand(commands.Cog):
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
        
        return True, f"✅ Куплено **{item['name']}** за {item['price']} ПК!\n💰 Новий баланс: {new_balance} ПК"

    class UnifiedShopView(discord.ui.View):
        def __init__(self, user, target_user, shop_cog):
            super().__init__(timeout=None)
            self.user = user
            self.target_user = target_user
            self.shop_cog = shop_cog
            self.current_mode = "inventory"  # inventory або shop
            self.current_page = 0
            self.items_per_page = 3

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            """Перевіряє чи користувач може використовувати інтерфейс"""
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
            
            if not stats.get('items'):
                embed.description = (
                    "```ansi\n"
                    "[0;37m📦 Інвентар порожній[0m\n\n"
                    "[0;36m💡 Купіть предмети в магазині[0m\n"
                    "[0;36m🛍️ Натисніть кнопку магазину нижче![0m\n"
                    "```"
                )
            else:
                # Розрахувати пагінацію
                items = stats['items']
                total_pages = (len(items) - 1) // self.items_per_page + 1
                start_idx = self.current_page * self.items_per_page
                end_idx = min(start_idx + self.items_per_page, len(items))
                page_items = items[start_idx:end_idx]
                
                # Показати предмети
                items_text = "```ansi\n"
                for i, item_id in enumerate(page_items):
                    item_number = start_idx + i + 1
                    if item_id in SHOP_ITEMS:
                        item = SHOP_ITEMS[item_id]
                        items_text += f"[0;37m{item_number}.[0m [1;32m{item['name']}[0m\n"
                        items_text += f"   [0;32m✅ {item['buff']}[0m\n"
                        items_text += f"   [0;31m❌ {item['debuff']}[0m\n\n"
                    else:
                        items_text += f"[0;37m{item_number}.[0m [0;31mНевідомий предмет[0m\n\n"
                items_text += "```"
                embed.description = items_text
                
                if total_pages > 1:
                    embed.set_footer(text=f"Сторінка {self.current_page + 1}/{total_pages}")
            
            # Інформація про слоти та баланс
            max_slots = 1 + (stats['wins'] // 10)
            total_value = sum(SHOP_ITEMS.get(item_id, {}).get('price', 0) for item_id in stats.get('items', []))
            
            info_text = f"```ansi\n[1;32m🎒 Слотів: {len(stats.get('items', []))}/{max_slots}[0m\n[0;33m💰 Баланс: {stats['pk_balance']} ПК[0m\n[0;35m💎 Вартість: {total_value} ПК[0m\n```"
            embed.add_field(name="📊 Статистика", value=info_text, inline=False)
            
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
            
            # Інформація про баланс
            max_slots = 1 + (stats['wins'] // 10)
            balance_info = f"```ansi\n[1;32m💰 Ваш баланс: {stats['pk_balance']} ПК[0m\n[0;37m🎒 Слотів вільно: {max_slots - len(stats['items'])}/{max_slots}[0m\n```"
            embed.add_field(name="💳 Ваші ресурси", value=balance_info, inline=False)
            
            # Показати предмети
            items = list(SHOP_ITEMS.items())
            total_pages = (len(items) - 1) // self.items_per_page + 1
            start_idx = self.current_page * self.items_per_page
            end_idx = min(start_idx + self.items_per_page, len(items))
            page_items = items[start_idx:end_idx]
            
            for item_id, item in page_items:
                # Визначити доступність
                can_afford = stats['pk_balance'] >= item['price']
                has_space = len(stats['items']) < max_slots
                already_owns = item_id in stats['items']
                
                if already_owns:
                    status = "✅ **Куплено**"
                    color_code = "[0;32m"
                elif can_afford and has_space:
                    status = "🟢 **Доступно**"
                    color_code = "[1;32m"
                elif not can_afford:
                    status = f"🔴 **Потрібно {item['price'] - stats['pk_balance']} ПК**"
                    color_code = "[0;31m"
                else:
                    status = "🟡 **Немає місця**"
                    color_code = "[1;33m"
                
                item_info = f"""```ansi
{color_code}{item['name']}[0m - [1;33m{item['price']} ПК[0m
[0;32m💚 {item['buff']}[0m
[0;31m💔 {item['debuff']}[0m

{status}
```"""
                
                embed.add_field(
                    name=f"{item.get('emoji', '⚡')} {item['name']}",
                    value=item_info,
                    inline=True
                )
            
            if total_pages > 1:
                embed.set_footer(text=f"Сторінка {self.current_page + 1}/{total_pages} • Всього предметів: {len(items)}")
            else:
                embed.set_footer(text=f"Всього предметів: {len(items)}")
            
            return embed

        async def update_view(self, interaction):
            """Оновити весь інтерфейс"""
            self.clear_items()
            
            if self.current_mode == "inventory":
                # Кнопки для інвентарю
                if self.target_user == self.user:
                    # Кнопка переходу в магазин
                    shop_btn = discord.ui.Button(
                        emoji="<:1405145855178182736:1405145855178182736>",
                        style=discord.ButtonStyle.primary,
                        row=0,
                        custom_id="switch_to_shop"
                    )
                    shop_btn.callback = self.switch_to_shop
                    self.add_item(shop_btn)
                
                # Кнопка оновлення
                refresh_btn = discord.ui.Button(
                    emoji="<:reset:1405110197248069733>",
                    style=discord.ButtonStyle.secondary,
                    row=0,
                    custom_id="refresh_inventory"
                )
                refresh_btn.callback = self.refresh_inventory
                self.add_item(refresh_btn)
                
                # Кнопки навігації для інвентарю
                stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
                items = stats.get('items', [])
                if items:
                    total_pages = (len(items) - 1) // self.items_per_page + 1
                    if total_pages > 1:
                        # Кнопка назад
                        if self.current_page > 0:
                            prev_btn = discord.ui.Button(
                                label="◀️ Назад",
                                style=discord.ButtonStyle.secondary,
                                row=1,
                                custom_id="prev_inventory"
                            )
                            prev_btn.callback = self.previous_page
                            self.add_item(prev_btn)
                        
                        # Кнопка вперед
                        if self.current_page < total_pages - 1:
                            next_btn = discord.ui.Button(
                                label="Далі ▶️",
                                style=discord.ButtonStyle.secondary,
                                row=1,
                                custom_id="next_inventory"
                            )
                            next_btn.callback = self.next_page
                            self.add_item(next_btn)
            
            else:  # shop mode
                # Кнопка повернення в інвентар
                inventory_btn = discord.ui.Button(
                    label="🎒 Інвентар",
                    style=discord.ButtonStyle.primary,
                    row=0,
                    custom_id="switch_to_inventory"
                )
                inventory_btn.callback = self.switch_to_inventory
                self.add_item(inventory_btn)
                
                # Кнопка оновлення
                refresh_btn = discord.ui.Button(
                    emoji="<:reset:1405110197248069733>",
                    style=discord.ButtonStyle.secondary,
                    row=0,
                    custom_id="refresh_shop"
                )
                refresh_btn.callback = self.refresh_shop
                self.add_item(refresh_btn)
                
                # Кнопки навігації для магазину
                items = list(SHOP_ITEMS.items())
                total_pages = (len(items) - 1) // self.items_per_page + 1
                if total_pages > 1:
                    # Кнопка назад
                    if self.current_page > 0:
                        prev_btn = discord.ui.Button(
                            label="◀️ Назад",
                            style=discord.ButtonStyle.secondary,
                            row=1,
                            custom_id="prev_shop"
                        )
                        prev_btn.callback = self.previous_page
                        self.add_item(prev_btn)
                    
                    # Кнопка вперед
                    if self.current_page < total_pages - 1:
                        next_btn = discord.ui.Button(
                            label="Далі ▶️",
                            style=discord.ButtonStyle.secondary,
                            row=1,
                            custom_id="next_shop"
                        )
                        next_btn.callback = self.next_page
                        self.add_item(next_btn)
                
                # Кнопки покупки для поточної сторінки магазину
                if self.target_user == self.user:  # Купувати можна тільки для себе
                    stats = await self.shop_cog.get_user_stats(self.target_user.id, interaction.guild.id)
                    start_idx = self.current_page * self.items_per_page
                    end_idx = min(start_idx + self.items_per_page, len(items))
                    page_items = items[start_idx:end_idx]
                    
                    for i, (item_id, item) in enumerate(page_items):
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
                        
                        btn = discord.ui.Button(
                            label=btn_label,
                            style=btn_style,
                            disabled=btn_disabled,
                            custom_id=f"buy_{item_id}",
                            row=2 + (i // 2)  # Розподіляти по рядках
                        )
                        btn.callback = self.create_buy_callback(item_id)
                        self.add_item(btn)

        def create_buy_callback(self, item_id):
            async def buy_callback(interaction):
                success, message = await self.shop_cog.buy_item(
                    self.target_user.id, 
                    interaction.guild.id, 
                    item_id
                )
                
                if success:
                    # Оновити інтерфейс після покупки
                    embed = await self.get_shop_embed(interaction)
                    await self.update_view(interaction)
                    await interaction.response.edit_message(embed=embed, view=self)
                    
                    # Надіслати повідомлення про успішну покупку
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            
            return buy_callback

        async def switch_to_shop(self, interaction):
            """Перемикнути на магазин"""
            if self.target_user != self.user:
                await interaction.response.send_message("❌ Магазин доступний тільки для власного профілю!", ephemeral=True)
                return
            
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

        async def refresh_inventory(self, interaction):
            """Оновити інвентар"""
            embed = await self.get_inventory_embed(interaction)
            await self.update_view(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

        async def refresh_shop(self, interaction):
            """Оновити магазин"""
            embed = await self.get_shop_embed(interaction)
            await self.update_view(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

    @app_commands.command(name="pidor_shop", description="Відкрити магазин та інвентар")
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
        
        view = self.UnifiedShopView(interaction.user, target_user, self)
        embed = await view.get_inventory_embed(interaction)
        await view.update_view(interaction)
        
        await interaction.followup.send(embed=embed, view=view)

    # Залишаємо старі команди для зворотної сумісності
    @app_commands.command(name="pidor_inventory", description="Показати інвентар гравця")
    @app_commands.describe(user="Чий інвентар показати (за замовчуванням - свій)")
    async def pidor_inventory_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        # Перенаправляємо на основну команду
        await self.pidor_shop_command(interaction, user)

async def setup(bot):
    await bot.add_cog(ShopInventoryCommand(bot))