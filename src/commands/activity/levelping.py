from discord import app_commands
import json
import discord

@bot.tree.command(name="levelping", description="Увімкнути або вимкнути пінг при підвищенні рівня")
@app_commands.describe(state="on або off")
async def levelping(interaction: discord.Interaction, state: str):
    user_id = str(interaction.user.id)

    try:
        with open("xp_data.json", "r") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    # Створити запис, якщо нема
    if user_id not in data:
        data[user_id] = {
            "xp": 0,
            "level": 1,
            "allow_level_ping": True  # за замовчуванням увімкнено
        }

    # Обробка команди
    if state.lower() == "off":
        data[user_id]["allow_level_ping"] = False
        msg = "🔕 Ви вимкнули пінги при підвищенні рівня."
    elif state.lower() == "on":
        data[user_id]["allow_level_ping"] = True
        msg = "🔔 Ви увімкнули пінги при підвищенні рівня."
    else:
        await interaction.response.send_message("❗ Використовуйте `on` або `off`.", ephemeral=True)
        return

    # Зберегти
    with open("xp_data.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(msg, ephemeral=True)
