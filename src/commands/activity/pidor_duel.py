import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime
import random
from modules.db import get_database

db = get_database()

class DuelRequestView(discord.ui.View):
    def __init__(self, challenger, target, timeout=60):
        super().__init__(timeout=timeout)
        self.challenger = challenger
        self.target = target

    @discord.ui.button(label="Прийняти", style=discord.ButtonStyle.success)
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("Це не тобі!", ephemeral=True)
            return

        winner, loser = (self.challenger, self.target) if random.random() < 0.5 else (self.target, self.challenger)

        # Зберегти історію
        await db.pidor_history.insert_one({
            "guild_id": interaction.guild.id,
            "winner": str(winner.id),
            "loser": str(loser.id),
            "timestamp": datetime.utcnow().isoformat()
        })

        # Оновити статистику переможця
        await db.pidor_stats.update_one(
            {"user_id": str(winner.id), "guild_id": interaction.guild.id},
            {"$inc": {"count": 1}},
            upsert=True
        )

        await interaction.response.edit_message(
            content=f"⚔️ **Дуель завершена!**\n\n**Переможець:** {winner.mention}\n**Невдаха:** {loser.mention} — пидор дня!",
            view=None
        )

    @discord.ui.button(label="Відхилити", style=discord.ButtonStyle.danger)
    async def decline(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.target:
            await interaction.response.send_message("Це не тобі!", ephemeral=True)
            return

        await interaction.response.edit_message(content="❌ Дуель відхилено.", view=None)

class PidorDuel(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pidor_duel", description="Викликати іншого користувача або рандома на дуель")
    @app_commands.describe(user="Кого викликати (опціонально)")
    async def duel(self, interaction: discord.Interaction, user: discord.Member = None):
        challenger = interaction.user

        if user:
            target = user
        else:
            candidates = [m for m in interaction.guild.members if not m.bot and m.status != discord.Status.offline and m != challenger]
            if not candidates:
                await interaction.response.send_message("Немає доступних гравців для дуелі.", ephemeral=True)
                return
            target = random.choice(candidates)

        if target == challenger:
            await interaction.response.send_message("Не можна викликати себе на дуель.", ephemeral=True)
            return

        view = DuelRequestView(challenger, target)
        await interaction.response.send_message(
            f"⚔️ {target.mention}, тебе викликає на дуель {challenger.mention}!\nПриймаєш виклик?",
            view=view
        )

async def setup(bot):
    await bot.add_cog(PidorDuel(bot))
