# views.py - Всі UI компоненти (View класи з кнопками)

import discord
from .constants import SHOP_ITEMS

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
        duel_cog = interaction.client.get_cog("PidorDuelCommand")
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
        profile_cog = interaction.client.get_cog("ProfileCommand")
        stats = await profile_cog.get_user_stats(self.target_user.id, interaction.guild.id)
        rank_info = profile_cog.get_rank_info(stats['wins'])
        
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
        profile_cog = interaction.client.get_cog("ProfileCommand")
        stats = await profile_cog.get_user_stats(self.target_user.id, interaction.guild.id)
        
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
        profile_cog = interaction.client.get_cog("ProfileCommand")
        stats = await profile_cog.get_user_stats(self.user.id, interaction.guild.id)
        
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

            profile_cog = interaction.client.get_cog("ProfileCommand")
            if profile_cog:
                success = await profile_cog.buy_item_inline(interaction, item_id)
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