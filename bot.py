import discord
from discord.ext import commands
import json
import os
from dotenv import load_dotenv

# Load configuration
try:
    with open("config.json", "r", encoding="utf-8") as f:
        config = json.load(f)
except FileNotFoundError:
    print("Error: config.json file not found")
    exit(1)
except json.JSONDecodeError:
    print("Error: Invalid JSON in config.json")
    exit(1)

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TOKEN")
if not TOKEN:
    print("Error: TOKEN not found in .env file")
    exit(1)

# Configure bot intents
intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.reactions = True
intents.voice_states = True
intents.message_content = True

# Initialize bot
bot = commands.Bot(command_prefix=config.get("prefix", "!"), intents=intents)

# Create data file if not exists
DATA_FILE = 'xp_data.json'
if not os.path.exists(DATA_FILE):
    with open(DATA_FILE, 'w') as f:
        json.dump({}, f)

async def load_extensions():
    # Load events
    for filename in os.listdir('./events'):
        if filename.endswith('.py'):
            await bot.load_extension(f'events.{filename[:-3]}')
    
    # Load commands from categories
    for category in os.listdir('./commands'):
        if os.path.isdir(f'./commands/{category}'):
            for filename in os.listdir(f'./commands/{category}'):
                if filename.endswith('.py'):
                    await bot.load_extension(f'commands.{category}.{filename[:-3]}')

@bot.event
async def on_ready():
    await load_extensions()
    print(f'Bot loaded with {len(bot.cogs)} cogs')

bot.run(TOKEN)