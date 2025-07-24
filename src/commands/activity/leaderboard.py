import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database

db = get_database()

class LeaderboardCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="leaderboard", description="Показує топ користувачів")
    async def leaderboard(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        users = await db.users.find({"guild_id": interaction.guild.id}).to_list(None)
        sorted_users = sorted(users, key=lambda x: x["xp"] + x["level"] * 1000, reverse=True)

        leaderboard_lines = ["📊 ЛІДЕРБОРД\n"]
        author_id = str(interaction.user.id)
        found_author = False

        for i, user_data in enumerate(sorted_users[:20], start=1):
            member = interaction.guild.get_member(user_data["user_id"])
            name = member.display_name if member else f"User#{user_data['user_id']}"

            line = (
                f"{i:>2}. {name:<20} | "
                f"Lvl: {user_data['level']:<2} | "
                f"XP: {user_data['xp']:<4} | "
                f"Voice: {user_data['voice_minutes']} хв | "
                f"Реакцій: {user_data['reactions']}"
            )
            leaderboard_lines.append(line)

            if user_data["user_id"] == interaction.user.id:
                found_author = True

        if not found_author:
            for i, user_data in enumerate(sorted_users, start=1):
                if user_data["user_id"] == interaction.user.id:
                    line = (
                        f"\nТи на {i} місці:\n"
                        f"Lvl: {user_data['level']} | XP: {user_data['xp']} | "
                        f"Voice: {user_data['voice_minutes']} хв | Реакцій: {user_data['reactions']}"
                    )
                    leaderboard_lines.append(line)
                    break

        result = "```\n" + "\n".join(leaderboard_lines) + "\n```"
        await interaction.followup.send(result)

async def setup(bot):
    await bot.add_cog(LeaderboardCommands(bot))