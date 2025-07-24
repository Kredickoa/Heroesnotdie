import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import os
from PIL import Image, ImageDraw, ImageFont
import io
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))


intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True
intents.voice_states = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)
TREE = bot.tree
DATA_FILE = 'xp_data.json'
LEVEL_UP_CHANNEL_NAME = "bots"

if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

def load_data():
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

def ensure_user(data, guild_id, user_id):
    if str(guild_id) not in data:
        data[str(guild_id)] = {}
    if str(user_id) not in data[str(guild_id)]:
        data[str(guild_id)][str(user_id)] = {
            "xp": 0,
            "level": 1,
            "messages": 0,
            "voice_minutes": 0,
            "reactions": 0
        }
    return data[str(guild_id)][str(user_id)]

def get_level_xp(level):
    return 5 * (level ** 2) + 50 * level + 100

async def level_up_check(message, user_data):
    needed_xp = get_level_xp(user_data["level"])
    if user_data["xp"] >= needed_xp:
        user_data["xp"] -= needed_xp
        user_data["level"] += 1

        channel = discord.utils.get(message.guild.text_channels, name=LEVEL_UP_CHANNEL_NAME)
        if channel:
            await channel.send(f"{message.author.mention} підвищив рівень до {user_data['level']}!")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    update_voice_time.start()
    await TREE.sync(guild=discord.Object(id=GUILD_ID))

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    data = load_data()
    user_data = ensure_user(data, message.guild.id, message.author.id)

    user_data["xp"] += 10
    user_data["messages"] += 1

    # ✅ Оновлюємо XP по даті
    today = datetime.now().strftime("%Y-%m-%d")
    if "history" not in user_data:
        user_data["history"] = {}
    user_data["history"][today] = user_data["history"].get(today, 0) + 10

    await level_up_check(message, user_data)
    save_data(data)
    await bot.process_commands(message)


@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return
    data = load_data()
    user_data = ensure_user(data, reaction.message.guild.id, user.id)

    user_data["xp"] += 2
    user_data["reactions"] += 1

    # ✅ Оновлюємо XP по даті
    today = datetime.now().strftime("%Y-%m-%d")
    if "history" not in user_data:
        user_data["history"] = {}
    user_data["history"][today] = user_data["history"].get(today, 0) + 2

    save_data(data)


@tasks.loop(minutes=1)
async def update_voice_time():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if not member.bot:
                    data = load_data()
                    user_data = ensure_user(data, guild.id, member.id)

                    user_data["xp"] += 5
                    user_data["voice_minutes"] += 1

                    # ✅ Оновлюємо XP по даті
                    today = datetime.now().strftime("%Y-%m-%d")
                    if "history" not in user_data:
                        user_data["history"] = {}
                    user_data["history"][today] = user_data["history"].get(today, 0) + 5

                    save_data(data)


# SLASH КОМАНДИ
@TREE.command(name="profile", description="Показує твій профіль", guild=discord.Object(id=GUILD_ID))
async def profile(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)

    try:
        data = load_data()
        user_data = ensure_user(data, interaction.guild.id, interaction.user.id)

        # Основна інформація
        current_level = user_data.get("level", 0)
        xp = user_data.get("xp", 0)
        xp_needed = get_level_xp(current_level)
        xp_percent = round((xp / xp_needed) * 100) if xp_needed else 0
        roles = [
            role.name for role in sorted(interaction.user.roles, key=lambda r: r.position, reverse=True)
            if role.name != "@everyone"
        ][:3]
        roles_display = ", ".join(roles) if roles else "Немає"
        joined_at = interaction.user.joined_at.strftime("%d %B %Y") if interaction.user.joined_at else "Невідомо"

        profile_text = f"""```
ПРОФІЛЬ: {interaction.user.display_name}
Учасник з: {joined_at}

Рівень: {current_level} | XP: {xp} / {xp_needed} ({xp_percent}%)
Voice: {user_data.get("voice_minutes", 0)} хв | Реакцій: {user_data.get("reactions", 0)} | Повідомлень: {user_data.get("messages", 0)}

Ролі: {roles_display}
```"""

        # ДОДАЄМО ГРАФІК
        import matplotlib.pyplot as plt
        from datetime import datetime, timedelta
        import uuid

        history = user_data.get("history", {})
        days = [datetime.now() - timedelta(days=i) for i in reversed(range(7))]
        labels = [day.strftime('%a') for day in days]
        xp_values = [history.get(day.strftime("%Y-%m-%d"), 0) for day in days]

        plt.figure(figsize=(8, 4))
        plt.plot(labels, xp_values, marker='o', linestyle='-', color='royalblue')
        plt.title('Активність (XP за останні 7 днів)')
        plt.xlabel('День тижня')
        plt.ylabel('Отримано XP')
        plt.grid(True)
        plt.tight_layout()

        # Унікальне ім’я файлу
        file_path = f"profile_graph_{uuid.uuid4().hex}.png"
        plt.savefig(file_path)
        plt.close()

        file = discord.File(file_path, filename="profile_graph.png")
        await interaction.followup.send(content=profile_text, file=file)

        # Видаляємо файл після відправки
        os.remove(file_path)

    except Exception as e:
        await interaction.followup.send(f"⚠️ Помилка при завантаженні профілю: `{e}`")



@TREE.command(name="leaderboard", description="Показує топ користувачів", guild=discord.Object(id=GUILD_ID))
async def leaderboard(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=False)
    data = load_data()
    users = data.get(str(interaction.guild.id), {})

    # Сортування: за total XP (XP + рівень * 1000)
    sorted_users = sorted(users.items(), key=lambda x: x[1]["xp"] + x[1]["level"] * 1000, reverse=True)

    leaderboard_lines = ["📊 ЛІДЕРБОРД\n"]
    author_id = str(interaction.user.id)
    found_author = False

    for i, (user_id, user_data) in enumerate(sorted_users[:20], start=1):
        member = interaction.guild.get_member(int(user_id))
        name = member.display_name if member else f"User#{user_id}"

        line = (
            f"{i:>2}. {name:<20} | "
            f"Lvl: {user_data['level']:<2} | "
            f"XP: {user_data['xp']:<4} | "
            f"Voice: {user_data['voice_minutes']} хв | "
            f"Реакцій: {user_data['reactions']}"
        )
        leaderboard_lines.append(line)

        if user_id == author_id:
            found_author = True

    if not found_author:
        for i, (user_id, user_data) in enumerate(sorted_users, start=1):
            if user_id == author_id:
                line = (
                    f"\nТи на {i} місці:\n"
                    f"Lvl: {user_data['level']} | XP: {user_data['xp']} | "
                    f"Voice: {user_data['voice_minutes']} хв | Реакцій: {user_data['reactions']}"
                )
                leaderboard_lines.append(line)
                break

    result = "```\n" + "\n".join(leaderboard_lines) + "\n```"
    await interaction.followup.send(result)







# АДМІН СЛЕШИ
@TREE.command(name="addxp", description="Додати XP", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Кому додати", amount="Скільки XP")
async def add_xp(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
        return
    data = load_data()
    user_data = ensure_user(data, interaction.guild.id, user.id)
    user_data["xp"] += amount
    save_data(data)
    await interaction.response.send_message(f"✅ {amount} XP додано {user.mention}.", ephemeral=True)

@TREE.command(name="removexp", description="Забрати XP", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="У кого забрати", amount="Скільки XP")
async def remove_xp(interaction: discord.Interaction, user: discord.Member, amount: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
        return
    data = load_data()
    user_data = ensure_user(data, interaction.guild.id, user.id)
    user_data["xp"] = max(user_data["xp"] - amount, 0)
    save_data(data)
    await interaction.response.send_message(f"🗑️ {amount} XP забрано у {user.mention}.", ephemeral=True)

@TREE.command(name="setlevel", description="Задати рівень", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Кому", level="Новий рівень")
async def set_level(interaction: discord.Interaction, user: discord.Member, level: int):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
        return
    data = load_data()
    user_data = ensure_user(data, interaction.guild.id, user.id)
    user_data["level"] = level
    save_data(data)
    await interaction.response.send_message(f"🔧 Рівень {user.mention} встановлено на {level}.", ephemeral=True)

@TREE.command(name="resetxp", description="Скинути XP", guild=discord.Object(id=GUILD_ID))
@app_commands.describe(user="Кому")
async def reset_xp(interaction: discord.Interaction, user: discord.Member):
    if not interaction.user.guild_permissions.administrator:
        await interaction.response.send_message("Недостатньо прав.", ephemeral=True)
        return
    data = load_data()
    user_data = ensure_user(data, interaction.guild.id, user.id)
    user_data["xp"] = 0
    save_data(data)
    await interaction.response.send_message(f"🔄 XP {user.mention} скинуто до 0.", ephemeral=True)

bot.run(TOKEN)
