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

    @discord.ui.button(label='📜 Правила серверу', style=discord.ButtonStyle.primary)
    async def server_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📋 **Правила серверу:** https://docs.google.com/document/d/1DB0v409ZOYQo1XtnTS3zLmRovGO9yDj4WNnTZPBOfKs/edit?tab=t.0", 
            ephemeral=True
        )

    @discord.ui.button(label='🎮 Правила HOI4', style=discord.ButtonStyle.secondary)
    async def hoi4_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
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
        image_path = "assets/images/sso.jpg"
        try:
            if os.path.exists(image_path):
                file = discord.File(image_path, filename="sso.jpg")
                embed.set_image(url="attachment://sso.jpg")
                await interaction.response.send_message(embed=embed, file=file, view=HOI4RulesButtons(), ephemeral=True)
            else:
                await interaction.response.send_message(embed=embed, view=HOI4RulesButtons(), ephemeral=True)
        except Exception as e:
            print(f"Помилка з фото: {e}")
            await interaction.response.send_message(embed=embed, view=HOI4RulesButtons(), ephemeral=True)

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
                "Флот – доступний за кнопкою нижче"
            ),
            color=0x2b2d31
        )
        
        await interaction.response.send_message(embed=embed, view=GuidesButtons(), ephemeral=True)


# --- КНОПКИ ДЛЯ ГАЙДІВ ---
class GuidesButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

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
        await interaction.response.send_message(
            "🚢 **Гайд по флоту:** https://docs.google.com/document/d/1Q6bYRRyOPAebEZj0eBy0r-h9B7ftHTIY/edit", 
            ephemeral=True
        )


# --- КНОПКИ ДЛЯ HOI4 ---
class HOI4RulesButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='Основні правила гри', style=discord.ButtonStyle.primary)
    async def basic_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📜 **Основні правила гри:** https://docs.google.com/document/d/19_N0yTlB2WOOsMNCMA4kvndmxsLijfG-0iHHAzD9rqo/edit?tab=t.0#heading=h.45pvneze54ml", 
            ephemeral=True
        )

    @discord.ui.button(label='Неісторичні ігри', style=discord.ButtonStyle.secondary)
    async def non_historical(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "🎯 **Неісторичні ігри:** https://docs.google.com/document/d/1sDY5YZMJb1uSrUkySeFqQy7sWoCzucBgyx9IkT5qeCY/edit", 
            ephemeral=True
        )

    @discord.ui.button(label='Історичні ігри', style=discord.ButtonStyle.secondary)
    async def historical(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message(
            "📚 **Історичні ігри:** https://docs.google.com/document/d/1PMhIOESkCo-bxzmaiLFjB1jaDcMZIomW25hQLyEdXRk/edit", 
            ephemeral=True
        )

    @discord.ui.button(label='Кайзеррайх', style=discord.ButtonStyle.secondary)
    async def kaiserreich(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎖️ Кайзеррайх",
            description="**Правила для гри в модифікацію Kaiserreich**",
            color=0x8B4513
        )
        embed.add_field(
            name="📋 Документ з правилами",
            value="[Переглянути правила Кайзеррайх](https://docs.google.com/document/d/1Ko70bTb_9c9OVnn8ZpXJhvJIktvvKHIg_BRlzFKcwcw/edit)",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RulesSetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

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