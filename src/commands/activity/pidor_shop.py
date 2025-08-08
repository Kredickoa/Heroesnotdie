import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict
from modules.db import get_database
from ._constants import SHOP_ITEMS

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
        
        return True, f"✅ Куплено **{item['name']}** за {item['price']} ПК!\n💰 Новий баланс: {new_balance} ПК"

    class ShopView(discord.ui.View):
        def __init__(self, user, shop_cog):
            super().__init__(timeout=300)
            self.user = user
            self.shop_cog = shop_cog
            self.current_page = 0
            self.items_per_page = 3

        async def get_shop_embed(self, interaction):
            stats = await self.shop_cog.get_user_stats(self.user.id, interaction.guild.id)
            
            embed = discord.Embed(
                title="🛍️ МАГАЗИН ПРЕДМЕТІВ",
                color=0xF1C40F
            )
            
            embed.set_author(
                name=f"{self.user.display_name}",
                icon_url=self.user.display_avatar.url
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
                    name=f"{item['emoji'] if 'emoji' in item else '⚡'} {item['name']}",
                    value=item_info,
                    inline=True
                )
            
            # Додати пусте поле для вирівнювання
            if len(page_items) % 2 != 0:
                embed.add_field(name="\u200b", value="\u200b", inline=True)
            
            if total_pages > 1:
                embed.set_footer(text=f"Сторінка {self.current_page + 1}/{total_pages} • Всього предметів: {len(items)}")
            else:
                embed.set_footer(text=f"Всього предметів: {len(items)}")
            
            return embed

        async def update_buttons(self, interaction):
            self.clear_items()
            
            stats = await self.shop_cog.get_user_stats(self.user.id, interaction.guild.id)
            items = list(SHOP_ITEMS.items())
            total_pages = (len(items) - 1) // self.items_per_page + 1
            
            # Кнопки навігації
            if total_pages > 1:
                prev_btn = discord.ui.Button(
                    label="◀️ Назад",
                    style=discord.ButtonStyle.secondary,
                    disabled=self.current_page <= 0,
                    row=0
                )
                prev_btn.callback = self.previous_page
                self.add_item(prev_btn)
                
                next_btn = discord.ui.Button(
                    label="Далі ▶️",
                    style=discord.ButtonStyle.secondary,
                    disabled=self.current_page >= total_pages - 1,
                    row=0
                )
                next_btn.callback = self.next_page
                self.add_item(next_btn)
            
            # Кнопки покупки для поточної сторінки
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
                    row=1 + (i // 2)  # Розподіляти по рядках
                )
                btn.callback = self.create_buy_callback(item_id)
                self.add_item(btn)
            
            # Кнопка оновити
            refresh_btn = discord.ui.Button(
                label="🔄 Оновити",
                style=discord.ButtonStyle.success,
                row=3
            )
            refresh_btn.callback = self.refresh_shop
            self.add_item(refresh_btn)

        def create_buy_callback(self, item_id):
            async def buy_callback(interaction):
                if interaction.user != self.user:
                    await interaction.response.send_message("❌ Це не ваш магазин!", ephemeral=True)
                    return

                success, message = await self.shop_cog.buy_item(
                    self.user.id, 
                    interaction.guild.id, 
                    item_id
                )
                
                if success:
                    # Оновити інтерфейс після покупки
                    embed = await self.get_shop_embed(interaction)
                    await self.update_buttons(interaction)
                    await interaction.response.edit_message(embed=embed, view=self)
                    
                    # Надіслати повідомлення про успішну покупку
                    await interaction.followup.send(message, ephemeral=True)
                else:
                    await interaction.response.send_message(message, ephemeral=True)
            
            return buy_callback

        async def previous_page(self, interaction):
            if self.current_page > 0:
                self.current_page -= 1
                embed = await self.get_shop_embed(interaction)
                await self.update_buttons(interaction)
                await interaction.response.edit_message(embed=embed, view=self)

        async def next_page(self, interaction):
            items = list(SHOP_ITEMS.items())
            total_pages = (len(items) - 1) // self.items_per_page + 1
            
            if self.current_page < total_pages - 1:
                self.current_page += 1
                embed = await self.get_shop_embed(interaction)
                await self.update_buttons(interaction)
                await interaction.response.edit_message(embed=embed, view=self)

        async def refresh_shop(self, interaction):
            embed = await self.get_shop_embed(interaction)
            await self.update_buttons(interaction)
            await interaction.response.edit_message(embed=embed, view=self)

    @app_commands.command(name="pidor_shop", description="Відкрити магазин предметів")
    async def pidor_shop_command(self, interaction: discord.Interaction):
        await interaction.response.defer()
        
        view = self.ShopView(interaction.user, self)
        embed = await view.get_shop_embed(interaction)
        await view.update_buttons(interaction)
        
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ShopCommand(bot))