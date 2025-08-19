import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database
import webbrowser
import os

db = get_database()

# --- КНОПКИ ДЛЯ ГОЛОВНОГО ПОВІДОМЛЕННЯ ---
class RulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📜 Правила серверу', style=discord.ButtonStyle.primary, custom_id='server_rules_btn')
    async def server_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Відкриваємо посилання напряму
        embed = discord.Embed(
            title="📋 Правила серверу",
            description="[Натисніть тут, щоб переглянути правила серверу](https://docs.google.com/document/d/1DB0v409ZOYQo1XtnTS3zLmRovGO9yDj4WNnTZPBOfKs/edit?tab=t.0)",
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='🎮 Правила HOI4', style=discord.ButtonStyle.secondary, custom_id='hoi4_rules_btn')
    async def hoi4_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎮 Правила HOI4",
            description="[Натисніть тут, щоб переглянути правила HOI4](https://docs.google.com/document/d/1LQ9tpaG0uU2KXThB7Z95pTCUK0LFwjNKhA3Q9BUj4oI/edit?usp=sharing)",
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='📚 Гайди', style=discord.ButtonStyle.success, custom_id='guides_btn')
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
                "Флот – доступний за кнопкою нижче"
            ),
            color=0x2b2d31
        )
        
        await interaction.response.send_message(embed=embed, view=GuidesButtons(), ephemeral=True)


# --- КНОПКИ ДЛЯ ГАЙДІВ ---
class GuidesButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Шаблони дивізій, літаків і флоту', style=discord.ButtonStyle.secondary, custom_id='division_templates_btn')
    async def division_templates(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="В розробці",
            description="Цей гайд наразі знаходиться в розробці.",
            color=0xff9900
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Армійські механіки', style=discord.ButtonStyle.secondary, custom_id='army_mechanics_btn')
    async def army_mechanics(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="В розробці",
            description="Цей гайд наразі знаходиться в розробці.",
            color=0xff9900
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Авіація', style=discord.ButtonStyle.secondary, custom_id='aviation_btn')
    async def aviation(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="В розробці",
            description="Цей гайд наразі знаходиться в розробці.",
            color=0xff9900
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='Флот', style=discord.ButtonStyle.primary, custom_id='fleet_guide_btn')
    async def fleet_guide(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🚢 Гайд по флоту",
            description="[Натисніть тут, щоб переглянути гайд по флоту](https://docs.google.com/document/d/1Q6bYRRyOPAebEZj0eBy0r-h9B7ftHTIY/edit)",
            color=0x5865F2
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RulesSetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Додаємо persistent views при ініціалізації
        self.bot.add_view(RulesView())
        self.bot.add_view(GuidesButtons())

    @commands.command(name="рулес")
    async def setup_rules(self, ctx):
        # Перевіряємо права адміністратора
        if not ctx.author.guild_permissions.administrator:
            await ctx.send("❌ У вас немає прав для цієї команди!", delete_after=5)
            return

        # Видаляємо повідомлення з командою
        try:
            await ctx.message.delete()
        except:
            pass

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
                "Ознайомся з ігровими правилами Hearts of Iron IV для комфортної гри в нашій спільноті."
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=RulesView())


async def setup(bot):
    await bot.add_cog(RulesSetupCommands(bot))