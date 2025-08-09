# views.py - Оновлені UI компоненти для нової системи

import discord
from ._constants import SHOP_ITEMS, BATTLE_COMMENTS
import random

class DuelRequestView(discord.ui.View):
    def __init__(self, challenger, target, timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.target = target

    @discord.ui.button(label="⚔️ Прийняти дуель", style=discord.ButtonStyle.success, emoji="🎯")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("❌ Це не твій дуель, спостерігач!", ephemeral=True)
            return
        
        # Створити ефектний embed прийняття
        accept_embed = discord.Embed(
            title="⚡ ДУЕЛЬ ПРИЙНЯТО!",
            description=f"**{self.target.mention}** приймає виклик від **{self.challenger.mention}**!\n\n🔥 **Підготовка до бою...**",
            color=0xE67E22
        )
        accept_embed.set_footer(text="Система обирає першого стрільця...")
        
        await interaction.response.edit_message(embed=accept_embed, view=None)
        
        # Запуск дуелі через секунду для драматичності
        import asyncio
        await asyncio.sleep(1)
        
        duel_cog = interaction.client.get_cog("PidorDuelCommand")
        if duel_cog:
            await duel_cog.execute_duel(interaction, self.challenger, self.target)

    @discord.ui.button(label="❌ Відхилити", style=discord.ButtonStyle.danger, emoji="🏃")
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("❌ Це не твій дуель!", ephemeral=True)
            return

        decline_messages = [
            f"❌ {self.target.mention} злякався дуелі з {self.challenger.mention}! Слабак! 🐔",
            f"💨 {self.target.mention} втік від бою! {self.challenger.mention} залишається непереможним!",
            f"🏃‍♂️ {self.target.mention} обрав життя замість слави! {self.challenger.mention} чекає наступного героя!",
            f"😱 {self.target.mention} не готовий до такого рівня! {self.challenger.mention} шукає гідного опонента!"
        ]

        embed = discord.Embed(
            title="🏃‍♂️ ДУЕЛЬ ВІДХИЛЕНО!",
            description=random.choice(decline_messages),
            color=0xE74C3C
        )
        embed.set_footer(text="Можливо наступного разу буде сміливіше...")
        
        await interaction.response.edit_message(embed=embed, view=None)

    async def on_timeout(self):
        timeout_embed = discord.Embed(
            title="⏰ ЧАС ВИЙШОВ!",
            description=f"{self.target.mention} не відповів на виклик від {self.challenger.mention}.\n\n😴 Мабуть, спить або втік!",
            color=0x95A5A6
        )
        timeout_embed.set_footer(text="Час на відповідь: 60 секунд")
        
        try:
            # Знайти оригінальне повідомлення та оновити його
            message = None  # Треба передавати message до View
            if hasattr(self, 'message') and self.message:
                await self.message.edit(embed=timeout_embed, view=None)
        except:
            pass

class DuelBattleView(discord.ui.View):
    def __init__(self, shooter, opponent, battle_info, duel_cog, interaction_obj):
        super().__init__(timeout=30)
        self.shooter = shooter
        self.opponent = opponent
        self.battle_info = battle_info
        self.duel_cog = duel_cog
        self.interaction_obj = interaction_obj
        self.shot_taken = False

    @discord.ui.button(label="🔫 ПОСТРІЛ!", style=discord.ButtonStyle.danger, emoji="💥")
    async def shoot(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.shooter or self.shot_taken:
            if interaction.user != self.shooter:
                await interaction.response.send_message("❌ Не твоя черга стріляти, глядач!", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Ти вже стріляв!", ephemeral=True)
            return
        
        self.shot_taken = True
        
        # Показати анімацію пострілу
        shot_embed = discord.Embed(
            title="💥 ПОСТРІЛ!",
            description=f"**{self.shooter.mention}** стріляє...\n\n🎯 Визначається результат...",
            color=0xE67E22
        )
        
        await interaction.response.edit_message(embed=shot_embed, view=None)
        
        # Невелика затримка для напруги
        import asyncio
        await asyncio.sleep(1.5)
        
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
            timeout_embed = discord.Embed(
                title="⏰ ПРОСТРОЧЕНО!",
                description=f"**{self.shooter.mention}** не встиг стрельнути вчасно!\n\n💔 Автоматичний промах!",
                color=0x95A5A6
            )
            
            try:
                await self.interaction_obj.edit_original_response(embed=timeout_embed, view=None)
                
                # Обробити як промах
                import asyncio
                await asyncio.sleep(2)
                
                await self.duel_cog.process_shot(
                    self.interaction_obj,
                    self.shooter,
                    self.opponent, 
                    self.battle_info,
                    first_shot=True,
                    auto_miss=True
                )
            except:
                pass

# Додаткові компоненти для майбутніх функцій
class ConfirmationView(discord.ui.View):
    """Підтвердження дій (для видалення предметів, скидання статистики тощо)"""
    def __init__(self, user, action_text, timeout=30):
        super().__init__(timeout=timeout)
        self.user = user
        self.action_text = action_text
        self.confirmed = False

    @discord.ui.button(label="✅ Підтвердити", style=discord.ButtonStyle.success)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Це не ваше рішення!", ephemeral=True)
            return
        
        self.confirmed = True
        self.stop()
        
        await interaction.response.edit_message(
            content=f"✅ **Підтверджено!** {self.action_text}",
            view=None
        )

    @discord.ui.button(label="❌ Скасувати", style=discord.ButtonStyle.danger)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Це не ваше рішення!", ephemeral=True)
            return
        
        self.stop()
        
        await interaction.response.edit_message(
            content="❌ **Дію скасовано.**",
            view=None
        )

class PaginationView(discord.ui.View):
    """Універсальний компонент для пагінації"""
    def __init__(self, pages, user, timeout=300):
        super().__init__(timeout=timeout)
        self.pages = pages
        self.user = user
        self.current_page = 0

    @discord.ui.button(label="◀️", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Не ваша навігація!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        else:
            await interaction.response.send_message("❌ Це перша сторінка!", ephemeral=True)

    @discord.ui.button(label="▶️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Не ваша навігація!", ephemeral=True)
            return
        
        if self.current_page < len(self.pages) - 1:
            self.current_page += 1
            await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        else:
            await interaction.response.send_message("❌ Це остання сторінка!", ephemeral=True)

    @discord.ui.button(label="🔄 Оновити", style=discord.ButtonStyle.primary)
    async def refresh(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.user:
            await interaction.response.send_message("❌ Не ваша навігація!", ephemeral=True)
            return
        
        await interaction.response.edit_message(embed=self.pages[self.current_page], view=self)
        await interaction.followup.send("🔄 Оновлено!", ephemeral=True)

async def setup(bot):
    pass  # Views не потребують окремого завантаження