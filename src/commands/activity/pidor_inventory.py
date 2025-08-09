import discord
from discord.ext import commands
from discord import app_commands
from typing import Optional, Dict
from modules.db import get_database
from ._constants import SHOP_ITEMS, RANKS

db = get_database()

class InventoryCommand(commands.Cog):
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

    class InventoryView(discord.ui.View):
        def __init__(self, user, target_user, inventory_cog):
            super().__init__(timeout=300)
            self.user = user
            self.target_user = target_user
            self.inventory_cog = inventory_cog
            self.current_page = 0
            self.items_per_page = 5

        async def get_inventory_embed(self, interaction):
            stats = await self.inventory_cog.get_user_stats(self.target_user.id, interaction.guild.id)
            
            embed = discord.Embed(
                title="🎒 ІНВЕНТАР",
                color=0x9B59B6
            )
            
            embed.set_author(
                name=f"{self.target_user.display_name}",
                icon_url=self.target_user.display_avatar.url
            )
            
            if not stats.get('items'):
                embed.description = """
                ```
                📦 Інвентар порожній
                
                💡 Купіть предмети командою /pidor_shop
                🛍️ або перейдіть в магазин!
                ```
                """
                embed.set_footer(text="Слотів використано: 0/1")
                return embed
            
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
            
            # Інформація про слоти
            max_slots = 1 + (stats['wins'] // 10)
            embed.add_field(
                name="📊 Використання слотів",
                value=f"```\n🎒 Зайнято: {len(items)}/{max_slots}\n📈 +1 слот кожні 10 перемог```",
                inline=True
            )
            
            # Загальна вартість
            total_value = sum(SHOP_ITEMS.get(item_id, {}).get('price', 0) for item_id in items)
            embed.add_field(
                name="💰 Загальна вартість",
                value=f"```\n💎 {total_value} ПК```",
                inline=True
            )
            
            if total_pages > 1:
                embed.set_footer(text=f"Сторінка {self.current_page + 1}/{total_pages} • Слотів: {len(items)}/{max_slots}")
            else:
                embed.set_footer(text=f"Слотів використано: {len(items)}/{max_slots}")
            
            return embed

        async def update_buttons(self):
            self.clear_items()
            
            stats = await self.inventory_cog.get_user_stats(self.target_user.id, 0)
            items = stats.get('items', [])
            total_pages = (len(items) - 1) // self.items_per_page + 1 if items else 1
            
            if total_pages > 1:
                # Кнопка назад
                prev_btn = discord.ui.Button(
                    label="◀️ Назад",
                    style=discord.ButtonStyle.secondary,
                    disabled=self.current_page <= 0
                )
                prev_btn.callback = self.previous_page
                self.add_item(prev_btn)
                
                # Кнопка вперед
                next_btn = discord.ui.Button(
                    label="Далі ▶️",
                    style=discord.ButtonStyle.secondary,
                    disabled=self.current_page >= total_pages - 1
                )
                next_btn.callback = self.next_page
                self.add_item(next_btn)
            
            # Кнопка оновити
            refresh_btn = discord.ui.Button(
                label="🔄 Оновити",
                style=discord.ButtonStyle.primary,
                row=1
            )
            refresh_btn.callback = self.refresh_inventory
            self.add_item(refresh_btn)
            
            # Кнопка магазину (тільки для власного інвентарю)
            if self.target_user == self.user:
                shop_btn = discord.ui.Button(
                    label="🛍️ Магазин",
                    style=discord.ButtonStyle.success,
                    row=1
                )
                shop_btn.callback = self.open_shop
                self.add_item(shop_btn)

        async def previous_page(self, interaction):
            if self.current_page > 0:
                self.current_page -= 1
                embed = await self.get_inventory_embed(interaction)
                await self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)

        async def next_page(self, interaction):
            stats = await self.inventory_cog.get_user_stats(self.target_user.id, interaction.guild.id)
            items = stats.get('items', [])
            total_pages = (len(items) - 1) // self.items_per_page + 1 if items else 1
            
            if self.current_page < total_pages - 1:
                self.current_page += 1
                embed = await self.get_inventory_embed(interaction)
                await self.update_buttons()
                await interaction.response.edit_message(embed=embed, view=self)

        async def refresh_inventory(self, interaction):
            embed = await self.get_inventory_embed(interaction)
            await self.update_buttons()
            await interaction.response.edit_message(embed=embed, view=self)

        async def open_shop(self, interaction):
            if self.target_user != self.user:
                await interaction.response.send_message("❌ Магазин доступний тільки у власному інвентарі!", ephemeral=True)
                return
            
            # Тут можна викликати команду магазину або перенаправити
            await interaction.response.send_message(
                "🛍️ Для відкриття магазину використовуйте команду `/pidor_shop`!", 
                ephemeral=True
            )

    @app_commands.command(name="pidor_inventory", description="Показати інвентар гравця")
    @app_commands.describe(user="Чий інвентар показати (за замовчуванням - свій)")
    async def pidor_inventory_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        
        target_user = user or interaction.user
        
        # Перевірити чи це бот
        if target_user.bot:
            await interaction.followup.send(
                "🤖 Боти не мають інвентарів. Вони зберігають все в хмарі!",
                ephemeral=True
            )
            return
        
        view = self.InventoryView(interaction.user, target_user, self)
        embed = await view.get_inventory_embed(interaction)
        await view.update_buttons()
        
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(InventoryCommand(bot))