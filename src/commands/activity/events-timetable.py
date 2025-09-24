import discord
from discord import app_commands
from discord.ext import commands

class EventCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @app_commands.command(name="івент", description="Створити оголошення про івент")
    async def event(self, interaction: discord.Interaction):
        # Перший embed з зображенням
        embed1 = discord.Embed(color=0x2F3136)  # Темно-сірий колір
        embed1.set_image(url="https://i.imgur.com/ftmM1HG.png")
        
        # Другий embed з інформацією про івент
        embed2 = discord.Embed(
            title="**Gartic Phone** — HEROES NOT DIE",
            description="Гра, що поєднує «зламаний телефон» і малювання, де гравці по черзі малюють та підписують малюнки, створюючи кумедний ланцюжок інтерпретаці.",
            color=0x5865F2  # Discord синій колір
        )
        
        embed2.add_field(
            name="<:zirka:1412519774780395631> Ведучий",
            value="<@961262391314755665>",
            inline=True
        )
        
        embed2.add_field(
            name="<:cubok:1412519929726374109> Нагорада за перемогу",
            value="кастомна роль до слідуючого івенту",
            inline=True
        )
        
        embed2.add_field(
            name="<:kalendar:1412519787019501719> Початок івенту",
            value="27 вересня 2025 р. 17:35",
            inline=False
        )
        
        # Створюємо кнопки
        view = EventButtonsView()
        
        # Відправляємо повідомлення з прихованим пінгом ролі
        await interaction.response.send_message(
            content="||<@&1412151154699145318>||",
            embeds=[embed1, embed2], 
            view=view
        )

class EventButtonsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)  # Кнопки не зникнуть через час
    
    @discord.ui.button(
        label="Приєднатись", 
        style=discord.ButtonStyle.primary,
        emoji="🔗"
    )
    async def join_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Перенаправлення на канал
        await interaction.response.send_message(
            "Перейдіть до каналу для участі: https://discord.com/channels/1386300362595504159/1401581412682960896",
            ephemeral=True
        )
    
    @discord.ui.button(
        label="Відправити жалобу",
        style=discord.ButtonStyle.secondary,
        emoji="⚠️"
    )
    async def report_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Відкриваємо модальне вікно для жалоби
        modal = ReportModal()
        await interaction.response.send_modal(modal)

class ReportModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Відправити жалобу")
        
        self.report_input = discord.ui.TextInput(
            label="Розкажіть нам про ситуацію максимально детально",
            placeholder="Опишіть вашу жалобу тут...",
            style=discord.TextStyle.paragraph,
            max_length=1000,
            required=True
        )
        self.add_item(self.report_input)
    
    async def on_submit(self, interaction: discord.Interaction):
        # Надсилаємо жалобу в спеціальний канал
        report_channel = interaction.client.get_channel(1403706530100023386)
        if report_channel:
            embed = discord.Embed(
                title="Нова жалоба",
                description=self.report_input.value,
                color=0xFF0000
            )
            embed.set_author(name=f"{interaction.user}", icon_url=interaction.user.avatar.url if interaction.user.avatar else None)
            embed.add_field(name="Користувач ID", value=interaction.user.id, inline=True)
            if interaction.guild:
                embed.add_field(name="Сервер", value=interaction.guild.name, inline=True)
            await report_channel.send(embed=embed)
        
        await interaction.response.send_message(
            "Дякуємо! Ваша жалоба була відправлена адміністрації.", 
            ephemeral=True
        )

async def setup(bot):
    await bot.add_cog(EventCommand(bot))