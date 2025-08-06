import discord
from discord.ext import commands
from discord import app_commands
from modules.db import get_database

db = get_database()

class PidorTop(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="pidor_top", description="Топ підорів дня")
    async def pidor_top(self, interaction: discord.Interaction):
        guild_id = interaction.guild.id
        stats = await db.pidor_stats.find({"guild_id": guild_id}).to_list(length=10)
        stats.sort(key=lambda x: x.get("count", 0), reverse=True)

        if not stats:
            await interaction.response.send_message("Ще немає жодного підора дня.", ephemeral=True)
            return

        description = ""
        for i, stat in enumerate(stats, start=1):
            user = interaction.guild.get_member(int(stat["user_id"]))
            name = user.mention if user else f"`{stat['user_id']}`"
            count = stat.get("count", 0)
            description += f"**{i}.** {name} — {count} перемог\n"

        embed = discord.Embed(title="🏆 Топ підорів дня", description=description, color=discord.Color.gold())
        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(PidorTop(bot))
