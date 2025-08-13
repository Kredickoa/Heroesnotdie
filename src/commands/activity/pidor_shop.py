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
            return False, "Невідомий предмет!"
        
        stats = await self.get_user_stats(user_id, guild_id)
        item = SHOP_ITEMS[item_id]
        
        if stats['pk_balance'] < item['price']:
            return False, f"Недостатньо ПК! Потрібно {item['price']} ПК"
        
        max_slots = 1 + (stats['wins'] // 10)
        if len(stats['items']) >= max_slots:
            return False, f"Інвентар заповнений! Слотів: {max_slots}"
        
        if item_id in stats['items']:
            return False, f"У вас вже є {item['name']}!"
        
        new_balance = stats['pk_balance'] - item['price']
        new_items = stats['items'] + [item_id]
        
        await db.duel_stats.update_one(
            {"user_id": str(user_id), "guild_id": guild_id},
            {"$set": {"pk_balance": new_balance, "items": new_items}}
        )
        
        return True, f"Куплено {item['name']} за {item['price']} ПК"

    class ShopView(discord.ui.View):
        def __init__(self, user, target_user, shop_cog):
            super().__init__(timeout=300)
            self.user = user
            self.target_user = target_user
            self.shop_cog = shop_cog
            self.current_mode = "inventory"
            self.current_page = 0
            self.items_per_page = 5
            self.selected_item = None

        async def interaction_check(self, interaction: discord.Interaction) -> bool:
            if interaction.user != self.user:
                await interaction.response.send_message("Це не твій інтерфейс!", ephemeral=True)
                return False
            return True

        async def get_inventory_embed(self):
            """Конфетний ембед для інвентарю"""
            stats = await self.shop_cog.get_user_stats(self.target_user.id, self.ctx.guild.id)
            max_slots = 1 + (stats['wins'] // 10)
            
            embed = discord.Embed(
                title=f"ІНВЕНТАР | {self.target_user.display_name}",
                color=0xFFD700  # Золотий колір
            )
            
            # Статистика
            embed.add_field(
                name="Ресурси",
                value=(
                    f"**Баланс:** {stats['pk_balance']} ПК\n"
                    f"**Слоти:** {len(stats['items']}/{max_slots}\n"
                    f"**Перемоги:** {stats['wins']} | **Поразки:** {stats['losses']}"
                ),
                inline=False
            )
            
            # Предмети
            items_text = ""
            if not stats['items']:
                items_text = "Інвентар порожній"
            else:
                items = stats['items']
                start_idx = self.current_page * self.items_per_page
                for i, item_id in enumerate(items[start_idx:start_idx+self.items_per_page], start_idx):
                    item = SHOP_ITEMS.get(item_id, {})
                    items_text += f"**{i+1}.** {item.get('name', 'Невідомий предмет')}\n"
            
            embed.add_field(name="Предмети", value=items_text or "Пусто", inline=False)
            embed.set_footer(text=f"Сторінка {self.current_page+1}")
            return embed

        async def get_shop_embed(self):
            """Конфетний ембед для магазину"""
            stats = await self.shop_cog.get_user_stats(self.target_user.id, self.ctx.guild.id)
            max_slots = 1 + (stats['wins'] // 10)
            
            embed = discord.Embed(
                title="МАГАЗИН ПРЕДМЕТІВ",
                color=0x00FF00  # Зелений колір
            )
            
            # Інформація
            embed.add_field(
                name="Ресурси",
                value=(
                    f"**Баланс:** {stats['pk_balance']} ПК\n"
                    f"**Вільні слоти:** {max_slots - len(stats['items'])}/{max_slots}"
                ),
                inline=False
            )
            
            # Список товарів
            items = list(SHOP_ITEMS.items())
            shop_text = ""
            start_idx = self.current_page * self.items_per_page
            for i, (item_id, item) in enumerate(items[start_idx:start_idx+self.items_per_page], start_idx):
                owned = " ✓" if item_id in stats['items'] else ""
                shop_text += f"**{i+1}.** {item['name']} - {item['price']} ПК{owned}\n"
            
            embed.add_field(name="Асортимент", value=shop_text or "Пусто", inline=False)
            embed.set_footer(text=f"Сторінка {self.current_page+1}")
            return embed

        async def update_view(self):
            """Оптимізований інтерфейс кнопок"""
            self.clear_items()
            
            # Навігаційні кнопки
            if self.current_mode == "inventory":
                self.add_item(SwitchButton("🛍️ Магазин", "shop"))
                items = (await self.shop_cog.get_user_stats(self.target_user.id, self.ctx.guild.id))['items']
                if items:
                    self.add_item(NavButton("◀️", "prev"))
                    self.add_item(NavButton("▶️", "next"))
            else:
                self.add_item(SwitchButton("🎒 Інвентар", "inventory"))
                self.add_item(NavButton("◀️", "prev"))
                self.add_item(NavButton("▶️", "next"))
                self.add_item(SelectMenu(self))
            
            self.add_item(ActionButton("🔄", "refresh"))

        @discord.ui.select(
            placeholder="Оберіть предмет",
            options=[discord.SelectOption(label=item['name'], value=item_id) 
                    for item_id, item in SHOP_ITEMS.items()]
        )
        async def select_callback(self, interaction, select):
            self.selected_item = select.values[0]
            await interaction.response.defer()

        @discord.ui.button(label="Купити", style=discord.ButtonStyle.primary)
        async def buy_callback(self, interaction, button):
            if not self.selected_item:
                await interaction.response.send_message("Оберіть предмет!", ephemeral=True)
                return
                
            success, msg = await self.shop_cog.buy_item(
                self.target_user.id, 
                interaction.guild.id, 
                self.selected_item
            )
            await interaction.response.send_message(msg, ephemeral=True)
            await self.refresh_view()

    class NavButton(discord.ui.Button):
        def __init__(self, emoji, action):
            super().__init__(emoji=emoji, style=discord.ButtonStyle.secondary)
            self.action = action
        
        async def callback(self, interaction):
            view = self.view
            if self.action == "prev" and view.current_page > 0:
                view.current_page -= 1
            elif self.action == "next":
                view.current_page += 1
            await view.refresh_view(interaction)

    class SwitchButton(discord.ui.Button):
        def __init__(self, label, mode):
            super().__init__(label=label, style=discord.ButtonStyle.primary)
            self.mode = mode
        
        async def callback(self, interaction):
            view = self.view
            view.current_mode = self.mode
            view.current_page = 0
            await view.refresh_view(interaction)

    class ActionButton(discord.ui.Button):
        def __init__(self, emoji, action):
            super().__init__(emoji=emoji, style=discord.ButtonStyle.secondary)
            self.action = action
        
        async def callback(self, interaction):
            await self.view.refresh_view(interaction)

    async def refresh_view(self, interaction):
        if self.current_mode == "inventory":
            embed = await self.get_inventory_embed()
        else:
            embed = await self.get_shop_embed()
        await self.update_view()
        await interaction.response.edit_message(embed=embed, view=self)

    @app_commands.command(name="pidor_shop", description="Магазин предметів для дуелей")
    async def pidor_shop_command(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        await interaction.response.defer()
        target_user = user or interaction.user
        
        if target_user.bot:
            await interaction.followup.send("Боти не мають інвентарів", ephemeral=True)
            return
        
        view = self.ShopView(interaction.user, target_user, self)
        view.ctx = interaction
        embed = await view.get_inventory_embed()
        await view.update_view()
        
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(ShopCommand(bot))