import discord
from discord.ext import commands
from discord import app_commands
from typing import Dict
from modules.db import get_database

db = get_database()

class RulesModule(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.config = {}

    async def load_config(self, guild_id: int):
        """Завантажити конфігурацію з бази даних"""
        config_data = await db.rules_config.find_one({"guild_id": guild_id})
        
        if not config_data:
            # Створити конфіг за замовчуванням
            default_config = {
                "guild_id": guild_id,
                "server_rules_url": "https://docs.google.com/document/d/1DB0v409ZOYQo1XtnTS3zLmRovGO9yDj4WNnTZPBOfKs/edit?tab=t.0",
                "hoi4_basic_rules_url": "https://docs.google.com/document/d/19_N0yTlB2WOOsMNCMA4kvndmxsLijfG-0iHHAzD9rqo/edit?tab=t.0#heading=h.45pvneze54ml",
                "hoi4_non_historical_url": "https://docs.google.com/document/d/1sDY5YZMJb1uSrUkySeFqQy7sWoCzucBgyx9IkT5qeCY/edit",
                "hoi4_historical_url": "https://docs.google.com/document/d/1PMhIOESkCo-bxzmaiLFjB1jaDcMZIomW25hQLyEdXRk/edit",
                "hoi4_kaiserreich_url": "https://docs.google.com/document/d/1Ko70bTb_9c9OVnn8ZpXJhvJIktvvKHIg_BRlzFKcwcw/edit",
                "fleet_guide_url": "https://docs.google.com/document/d/1Q6bYRRyOPAebEZj0eBy0r-h9B7ftHTIY/edit",
                "hoi4_image": "assets/images/sso.jpg"
            }
            await db.rules_config.insert_one(default_config)
            self.config = default_config
        else:
            self.config = config_data

    async def save_config(self, guild_id: int):
        """Зберегти конфігурацію в базу даних"""
        await db.rules_config.update_one(
            {"guild_id": guild_id},
            {"$set": self.config},
            upsert=True
        )

    # --- КНОПКИ ДЛЯ ГОЛОВНОГО ПОВІДОМЛЕННЯ ---
    class RulesView(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label='📜 Правила серверу', style=discord.ButtonStyle.primary)
        async def server_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Правила серверу",
                description="[Натисни тут для переходу до правил серверу](" + self.cog.config["server_rules_url"] + ")",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='🎮 Правила HOI4', style=discord.ButtonStyle.secondary)
        async def hoi4_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
            await self.cog.load_config(interaction.guild.id)
            
            embed = discord.Embed(
                title="Ігрові правила по Hearts of Iron IV",
                description=(
                    "На сервері регулярно проводяться ігрові партії по грі **HOI4** — зазвичай 1–2 рази на тиждень.\n\n"
                    "Для таких ігор ми створили окремий список правил, яких дотримується адміністрація та гравці.\n\n"
                    "*У разі порушення правил адміністрація може видати покарання, включно із забороною на участь у наступних іграх.*"
                ),
                color=0x2b2d31
            )
            
            # Прикріплення фото
            try:
                file = discord.File(self.cog.config["hoi4_image"], filename="hoi4_rules.jpg")
                embed.set_image(url="attachment://hoi4_rules.jpg")
                await interaction.response.send_message(embed=embed, file=file, view=self.cog.HOI4RulesButtons(self.cog), ephemeral=True)
            except FileNotFoundError:
                await interaction.response.send_message(embed=embed, view=self.cog.HOI4RulesButtons(self.cog), ephemeral=True)

        @discord.ui.button(label='📚 Гайди', style=discord.ButtonStyle.success)
        async def guides(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="ГАЙДИ",
                description=(
                    "створені з цілью допогти гравцям спільноти стати сильнішими та "
                    "досвідченішими в грі.\n\n"
                    "**Механіка гри**\n"
                    "Шаблони дивізій, літаків і флоту – в розробці.\n"
                    "Армійські механіки – в розробці.\n"
                    "Авіація – в розробці.\n"
                    "Флот – Посилання"
                ),
                color=0x2b2d31
            )
            
            await interaction.response.send_message(embed=embed, view=self.cog.GuidesButtons(self.cog), ephemeral=True)

    # --- КНОПКИ ДЛЯ ГАЙДІВ ---
    class GuidesButtons(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label='Шаблони дивізій, літаків і флоту', style=discord.ButtonStyle.secondary)
        async def division_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="В розробці",
                description="Цей гайд наразі знаходиться в розробці.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='Армійські механіки', style=discord.ButtonStyle.secondary)
        async def army_mechanics(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="В розробці",
                description="Цей гайд наразі знаходиться в розробці.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='Авіація', style=discord.ButtonStyle.secondary)
        async def aviation(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="В розробці",
                description="Цей гайд наразі знаходиться в розробці.",
                color=0xff9900
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='Флот', style=discord.ButtonStyle.primary)
        async def fleet_guide(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Гайд по флоту",
                description="[Натисни тут для переходу до гайду по флоту](" + self.cog.config["fleet_guide_url"] + ")",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- КНОПКИ ДЛЯ HOI4 ---
    class HOI4RulesButtons(discord.ui.View):
        def __init__(self, cog):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label='Основні правила гри', style=discord.ButtonStyle.primary)
        async def basic_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Основні правила гри",
                description="[Натисни тут для переходу до основних правил гри](" + self.cog.config["hoi4_basic_rules_url"] + ")",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='Неісторичні ігри', style=discord.ButtonStyle.secondary)
        async def non_historical(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Неісторичні ігри",
                description="[Натисни тут для переходу до правил неісторичних ігор](" + self.cog.config["hoi4_non_historical_url"] + ")",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='Історичні ігри', style=discord.ButtonStyle.secondary)
        async def historical(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Історичні ігри",
                description="[Натисни тут для переходу до правил історичних ігор](" + self.cog.config["hoi4_historical_url"] + ")",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

        @discord.ui.button(label='Кайзеррайх', style=discord.ButtonStyle.secondary)
        async def kaiserreich(self, interaction: discord.Interaction, button: discord.ui.Button):
            embed = discord.Embed(
                title="Кайзеррайх",
                description="[Натисни тут для переходу до правил Кайзеррайх](" + self.cog.config["hoi4_kaiserreich_url"] + ")",
                color=0x00ff00
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)

    # --- КОМАНДИ ---
    @app_commands.command(name="setup_rules", description="Створити повідомлення з правилами")
    async def setup_rules_command(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ У вас немає прав для цієї команди!", ephemeral=True)
            return

        await self.load_config(interaction.guild.id)

        embed = discord.Embed(color=0x2f3136)
        embed.add_field(
            name="**• Ласкаво просимо на сервер!**",
            value=(
                "• Радий бачити тебе на нашому сервері! Щоб швидко влитися у спільноту та стати активним учасником, "
                "ознайомся з основними розділами серверу за допомогою кнопок нижче. Це допоможе освоїтися, "
                "уникнути порушень та зробить твоє перебування приємним і цікавим.\n\n"
                "**Бажаємо гарного часу та цікавих знайомств!**"
            ),
            inline=False
        )
        embed.add_field(
            name="**📋 • Інформація по серверу:**",
            value=(
                "**📕 Правила серверу**\n"
                "Ознайомся, щоб підтримувати дружню атмосферу та взаємоповагу.\n\n"
                "**🎮 Правила HOI4**\n"
                "Ознайомся з ігровими правилами Hearts of Iron IV для комфортної гри в нашій спільноті.\n\n"
                "**📚 Гайди**\n"
                "Корисні гайди та поради для покращення навичок гри в Hearts of Iron IV."
            ),
            inline=False
        )

        await interaction.response.send_message(embed=embed, view=self.RulesView(self))

    @app_commands.command(name="edit_rules", description="Редагувати налаштування правил")
    @app_commands.describe(
        setting="Що редагувати",
        value="Нове значення"
    )
    @app_commands.choices(setting=[
        app_commands.Choice(name="Правила серверу", value="server_rules_url"),
        app_commands.Choice(name="HOI4 - Основні правила", value="hoi4_basic_rules_url"),
        app_commands.Choice(name="HOI4 - Неісторичні ігри", value="hoi4_non_historical_url"),
        app_commands.Choice(name="HOI4 - Історичні ігри", value="hoi4_historical_url"),
        app_commands.Choice(name="HOI4 - Кайзеррайх", value="hoi4_kaiserreich_url"),
        app_commands.Choice(name="Гайд по флоту", value="fleet_guide_url"),
        app_commands.Choice(name="Фото HOI4", value="hoi4_image")
    ])
    async def edit_rules_command(self, interaction: discord.Interaction, setting: str, value: str):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ У вас немає прав для цієї команди!", ephemeral=True)
            return

        await self.load_config(interaction.guild.id)
        old_value = self.config.get(setting, "Не встановлено")
        
        # Оновити в базі даних
        await db.rules_config.update_one(
            {"guild_id": interaction.guild.id},
            {"$set": {setting: value}},
            upsert=True
        )
        
        # Оновити локальний конфіг
        self.config[setting] = value

        embed = discord.Embed(
            title="✅ Налаштування оновлено",
            description=f"**Параметр:** {setting}\n**Старе значення:** {old_value}\n**Нове значення:** {value}",
            color=0x00ff00
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @app_commands.command(name="show_rules_config", description="Показати поточні налаштування правил")
    async def show_config_command(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("❌ У вас немає прав для цієї команди!", ephemeral=True)
            return

        await self.load_config(interaction.guild.id)

        embed = discord.Embed(
            title="⚙️ Поточні налаштування правил",
            color=0x3498db
        )
        
        settings_names = {
            "server_rules_url": "📜 Правила серверу",
            "hoi4_basic_rules_url": "🎮 HOI4 - Основні правила",
            "hoi4_non_historical_url": "🎮 HOI4 - Неісторичні ігри",
            "hoi4_historical_url": "🎮 HOI4 - Історичні ігри", 
            "hoi4_kaiserreich_url": "🎮 HOI4 - Кайзеррайх",
            "fleet_guide_url": "🚢 Гайд по флоту",
            "hoi4_image": "🖼️ Фото HOI4"
        }
        
        for key, value in self.config.items():
            if key != "guild_id" and key != "_id":
                display_name = settings_names.get(key, key)
                embed.add_field(
                    name=display_name,
                    value=f"`{value}`",
                    inline=False
                )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(RulesModule(bot))