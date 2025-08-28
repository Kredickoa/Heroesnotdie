import discord
from discord import app_commands
from discord.ext import commands
from modules.db import get_database
import webbrowser
import os

db = get_database()

# --- КНОПКИ ДЛЯ ГОЛОВНОГО ПОВІДОМЛЕННЯ ---
class MainMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📋 Інформація про сервер', style=discord.ButtonStyle.primary, custom_id='server_info_btn')
    async def server_info(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="📋 • Інформація про сервер",
            color=0xc0c0c0
        )
        embed.add_field(
            name="```— Правила сервера```",
            value="Ознайомтеся з ними, щоб підтримувати дружню атмосферу.",
            inline=False
        )
        embed.add_field(
            name="```— Ролі```",
            value="Дізнайтеся, які ролі доступні та як їх отримати.",
            inline=False
        )
        embed.add_field(
            name="```— Ролі за натисканням```",
            value="Автоматична видача корисних ролей для взаємодії із сервером.",
            inline=False
        )
        embed.add_field(
            name="```— ЧаПи```",
            value="Відповіді на часті запитання та не тільки.",
            inline=False
        )
        embed.add_field(
            name="```— ігрова категорія```",
            value="правила ігор на сервері, гайди, тощо.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, view=ServerInfoButtons(), ephemeral=True)

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
            color=0xc0c0c0
        )
        
        await interaction.response.send_message(embed=embed, view=GuidesButtons(), ephemeral=True)

    @discord.ui.button(label='🎮 Правила HOI4', style=discord.ButtonStyle.secondary, custom_id='hoi4_rules_btn')
    async def hoi4_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎮 Правила HOI4",
            description="[Натисніть тут, щоб переглянути правила HOI4](https://docs.google.com/document/d/1LQ9tpaG0uU2KXThB7Z95pTCUK0LFwjNKhA3Q9BUj4oI/edit?usp=sharing)",
            color=0xc0c0c0
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# --- КНОПКИ ДЛЯ ІНФОРМАЦІЇ ПРО СЕРВЕР ---
class ServerInfoButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='📜 Правила серверу', style=discord.ButtonStyle.danger, custom_id='server_rules_detailed_btn')
    async def server_rules_detailed(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```Правила серверу Heroes not die```",
            color=0xc0c0c0
        )
        
        # Правило 1
        embed.add_field(
            name="**1. Повага до інших**",
            value=(
                "заборонені образи, приниження, тролінг, цькування, провокації та будь-які прояви токсичності.\n"
                "1.1 Мовний етикет — не зловживайте нецензурною лексикою, уникайте хамства та агресивного тону.\n"
                "1.2 Адекватність — підтримуйте конструктивне спілкування, не створюйте конфліктів без причини.\n"
                "1.3 Модерація — адміністрація залишає за собою право видаляти контент або користувачів, що заважають атмосфері сервера.\n"
                "1.4 ЛС (приватні повідомлення) не модерується, якщо тільки це не є спам-розсилка.\n"
                "1.5 Незнання правил не звільняє від відповідальності.\n"
                "1.6 Адміністрація може застосовувати заходи навіть без прямого порушення, якщо поведінка шкодить серверам."
            ),
            inline=False
        )
        
        # Правило 2
        embed.add_field(
            name="**2. Заборонений контент**",
            value=(
                "2.1 Заборонено публікувати порнографію або сексуальний контент так само не можна оглядати це у голових каналах (виняток нсф канал).\n"
                "2.2 Заборонено сцени надмірного насильства, жорстокості чи крові.\n"
                "2.3 Заборонено контент, що негативно впливає на слух, зір або психіку учасників.\n"
                "2.4 Заборонено заклики до ненависті, дискримінації за будь-якою ознакою.\n"
                "2.5 Заборонено політичну або релігійну пропаганду у провокативній формі.\n"
                "2.6 Заборонено заклики до шкідливих чи незаконних дій.\n"
                "**Наказання:** попередження/бан, від 90 днів до ∞."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=RulesDetailsView(), ephemeral=True)

    @discord.ui.button(label='🎭 Ролі', style=discord.ButtonStyle.primary, custom_id='roles_btn')
    async def roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="🎭 • Ролі сервера",
            color=0xc0c0c0
        )
        await interaction.response.send_message(embed=embed, view=RolesMenuView(), ephemeral=True)

    @discord.ui.button(label='❓ FAQ', style=discord.ButtonStyle.secondary, custom_id='faq_btn')
    async def faq(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="❓ • Часті питання (FAQ)",
            color=0xc0c0c0
        )
        await interaction.response.send_message(embed=embed, view=FAQView(), ephemeral=True)


# --- КНОПКИ ДЛЯ РОЛЕЙ ---
class RolesMenuView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🛡️ Персонал', style=discord.ButtonStyle.danger, custom_id='staff_roles_btn')
    async def staff_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```🛡️・Персонал:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="<@&1386305553919119450> @✚ — власники сервера",
            value="ID ролі: `1386305553919119450`",
            inline=False
        )
        embed.add_field(
            name="<@&1410532910989312000> @✓ — адміністрація сервера",
            value="ID ролі: `1410532910989312000`",
            inline=False
        )
        embed.add_field(
            name="<@&1404790445040472115> @C u r a t o r — вища модерація сервера",
            value="ID ролі: `1404790445040472115`",
            inline=False
        )
        embed.add_field(
            name="<@&1387889015159656528> @M o d e r a t o r — модерація сервера",
            value="ID ролі: `1387889015159656528`",
            inline=False
        )
        embed.add_field(
            name="<@&1403092677162958878> @H e l p e r — нижча модерація сервера",
            value="ID ролі: `1403092677162958878`",
            inline=False
        )
        embed.add_field(
            name="<@&1386307351824568461> @H o s t — ведучі заходів сервера",
            value="ID ролі: `1386307351824568461`",
            inline=False
        )
        embed.add_field(
            name="<@&1404791155639455776> @D e b u g g e r — наглядачі за економікою сервера",
            value="ID ролі: `1404791155639455776`",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='📌 Основні', style=discord.ButtonStyle.primary, custom_id='main_roles_btn')
    async def main_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```📌・Основні:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="<@&1404791339174068284> @🤝Friend — Друзі сервера",
            value="Довірені особи адміністрації сервера.\nID ролі: `1404791339174068284`",
            inline=False
        )
        embed.add_field(
            name="<@&1404791889554702437> @Media — Відеоблогери",
            value="Учасники з більш ніж 10 000 підписників на YouTube / 10 000 підписників у TikTok / 10 000 фоловерів на Twitch.\nID ролі: `1404791889554702437`",
            inline=False
        )
        embed.add_field(
            name="<@&1404791450700611764> @Nitro Booster — Бустери сервера",
            value="Ті, хто підтримали сервер за допомогою Nitro.\nID ролі: `1404791450700611764`",
            inline=False
        )
        embed.add_field(
            name="<@&1404791751058657400> @C r u s a d e r — Еліта сервера",
            value="Ті, хто зробили внесок у розвиток сервера.\nID ролі: `1404791751058657400`",
            inline=False
        )
        embed.add_field(
            name="<@&1404791630266892428> @Girls — Дівчата сервера",
            value="Пройшли перевірку статі у голосовому каналі.\nЦе можна зробити відмітивши когось з стафу серверу або ж через тікет подавшись на цю роль.\nID ролі: `1404791630266892428`",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='🍭 Активність', style=discord.ButtonStyle.success, custom_id='activity_roles_btn')
    async def activity_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```🍭・Активність:```",
            color=0xc0c0c0
        )
        await interaction.response.send_message(embed=embed, view=ActivityRolesView(), ephemeral=True)


# --- КНОПКИ ДЛЯ АКТИВНОСТІ ---
class ActivityRolesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🎤 Щотижнева активність', style=discord.ButtonStyle.secondary, custom_id='weekly_activity_btn')
    async def weekly_activity(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```🎤・Ролі за щотижневу активність:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="<@&1410590484514213908> @25/8 — за топ 5 войсу/чату",
            value="ID ролі: `1410590484514213908`",
            inline=False
        )
        embed.add_field(
            name="<@&1410607858424483940> @✏️ — за топ 15 чату",
            value="ID ролі: `1410607858424483940`",
            inline=False
        )
        embed.add_field(
            name="<@&1410607898534608957> @🎤 — за топ 15 войсу",
            value="ID ролі: `1410607898534608957`",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='⬆️ Ролі за рівень', style=discord.ButtonStyle.primary, custom_id='level_roles_btn')
    async def level_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```⬆️・Ролі за рівень:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="<@&1410607953932976261> @Ultralegendary — за 100 рівень",
            value="ID ролі: `1410607953932976261`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608009843052634> @Legendary — за 80 рівень",
            value="ID ролі: `1410608009843052634`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608051723174030> @Mythic — за 60 рівень",
            value="ID ролі: `1410608051723174030`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608162159067248> @Epic — за 40 рівень",
            value="ID ролі: `1410608162159067248`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608204634918922> @Super Rare — за 25 рівень",
            value="ID ролі: `1410608204634918922`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608242425593896> @Rare — за 10 рівень",
            value="ID ролі: `1410608242425593896`",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='🎤 Голосова активність', style=discord.ButtonStyle.success, custom_id='voice_activity_btn')
    async def voice_activity(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```🎤・Ролі за голосову активність:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="<@&1410608337472585738> @Echo — за 1000 годин",
            value="ID ролі: `1410608337472585738`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608371928662180> @Vox — за 750 годин",
            value="ID ролі: `1410608371928662180`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608425984983274> @Siren — за 500 годин",
            value="ID ролі: `1410608425984983274`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608454371901562> @Noise — за 250 годин",
            value="ID ролі: `1410608454371901562`",
            inline=False
        )
        embed.add_field(
            name="<@&1410608485661671587> @Whisp — за 100 годин",
            value="ID ролі: `1410608485661671587`",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# --- FAQ VIEW ---
class FAQView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='🎭 Ролі', style=discord.ButtonStyle.primary, custom_id='faq_roles_btn')
    async def faq_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```🎭・Р О Л І:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="**Як отримати роль на сервері?**",
            value="Уважно ознайомтеся з розділом (🎭 — Ролі в цьому каналі). Якщо ви знайшли підхожу роль або у вас залишилися питання — пишіть [support](https://discord.com/channels/1386300362595504159/1403682856814903368)",
            inline=False
        )
        embed.add_field(
            name="**Як отримати ролі за досягнення в Brawl Stars?**",
            value="Щоб пройти верифікацію, введіть свій ігровий ID у команду, натиснувши на неї: `/verify`.\nДалі використовуйте команду `/menu`, яка дозволяє у будь-який момент зняти/видати доступні вам ролі.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='📢 Скарги', style=discord.ButtonStyle.danger, custom_id='faq_complaints_btn')
    async def faq_complaints(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```📢・С К А Р Г И:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="**Що робити, якщо вас образили?**",
            value="Якщо ви побачили повідомлення, яке вас образило — відкрийте тікет у ⁠📨・підтримка.",
            inline=False
        )
        embed.add_field(
            name="**Як подати скаргу?**",
            value="Подати її можна в каналі [support](https://discord.com/channels/1386300362595504159/1403682856814903368) за такою формою:\n\n**ID учасника.**\n\n**Порушення.**\n\n**Докази.**",
            inline=False
        )
        embed.add_field(
            name="**Як дізнатися ID учасника?**",
            value="1. Заходимо в налаштування у розділ «Розширені».\n2. Знаходимо «Режим розробника» та вмикаємо його.\n3. Переходимо в профіль користувача та натискаємо «…».\n4. Знаходимо та натискаємо «Скопіювати ID користувача».",
            inline=False
        )
        embed.add_field(
            name="**Що робити, якщо ви побачили порушення з боку модераторів?**",
            value="Відкрийте тікет у [support](https://discord.com/channels/1386300362595504159/1403682856814903368) і тегніть роль @C u r a t o r, прикріпивши скриншот із порушенням модератора.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label='💎 Бонуси', style=discord.ButtonStyle.success, custom_id='faq_bonuses_btn')
    async def faq_bonuses(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```💎・Б О Н У С И:```",
            color=0xc0c0c0
        )
        embed.add_field(
            name="**Як отримати власний войс?**",
            value="Якщо у вас є компанія з більш ніж 4 осіб і ви можете підтримувати активність у своєму войсі від 50 годин на тиждень — ви маєте можливість звернутися в [support](https://discord.com/channels/1386300362595504159/1403682856814903368), де вам безкоштовно створять власний войс і кастомну роль.",
            inline=False
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


# --- ДОДАТКОВІ ПРАВИЛА ---
class RulesDetailsView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='➡️ Більше правил', style=discord.ButtonStyle.secondary, custom_id='more_rules_btn')
    async def more_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```Правила серверу Heroes not die (продовження)```",
            color=0xc0c0c0
        )
        
        # Правило 3
        embed.add_field(
            name="**3. Спам та флуд**",
            value=(
                "Не флудити та не спамити без змісту (спам, флуд, оффтоп, капс).\n"
                "**Наказання:** мут/попередження, 30–360 хвилин або 45–180 днів.\n"
                "3.1 Використовувати @згадки лише за потреби.\n"
                "3.2 Повідомлення мають бути зрозумілими та по темі каналу.\n"
                "3.3 Заборонено зловживати емодзі, капсом або повторюваним текстом.\n"
                "3.4 Слідуйте правилам голосової кімнати укладеної її власником та дотримуйтесь головних правил серверу."
            ),
            inline=False
        )
        
        # Правило 4
        embed.add_field(
            name="**4. Голосові канали**",
            value=(
                "Використовувати мікрофон лише за призначенням — без шумів, музики чи сторонніх звуків.\n"
                "**Наказання:** попередження, 90–180 днів.\n"
                "4.1 Не перебивати інших, не кричати та не перекривати голоси.\n"
                "4.2 Дотримуватись теми розмови.\n"
                "4.3 Музика у войсах — лише за згодою всіх учасників.\n"
                "4.4 Порушення у войсах розглядаються лише за наявності відеозапису."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, view=FinalRulesView(), ephemeral=True)


class FinalRulesView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label='⚖️ Покарання та заключні правила', style=discord.ButtonStyle.danger, custom_id='final_rules_btn')
    async def final_rules(self, interaction: discord.Interaction, button: discord.ui.Button):
        embed = discord.Embed(
            title="```Правила серверу Heroes not die (заключна частина)```",
            color=0xc0c0c0
        )
        
        # Правила 5-7
        embed.add_field(
            name="**5. Шкідливі дії**",
            value=(
                "Не поширювати віруси, шкідливі програми чи підозрілі посилання.\n"
                "5.1 Шахрайські чи деструктивні дії проти сервера або його учасників.\n"
                "5.2 Зловживання привілеями.\n"
                "5.3 Повідомляйте адміністрацію про підозрілих користувачів чи порушення.\n"
                "**Наказання:** попередження/бан, від 90 днів до ∞."
            ),
            inline=False
        )
        
        embed.add_field(
            name="**6. Покарання**",
            value=(
                "— попередження (усне або текстове)\n"
                "— тимчасовий мут (від 30 хв до 360 хв)\n"
                "— тимчасове обмеження доступу до каналів\n"
                "— тимчасовий бан (від 45 днів)\n"
                "— перманентний бан\n\n"
                "6.1 Повторні порушення ведуть до посилення покарань.\n"
                "6.2 Покарання застосовуються на розсуд модерації.\n"
                "6.3 Адміністрація має право обмежити доступ до каналів за окремі порушення.\n"
                "6.4 Рішення адміністрації можна оскаржити у спеціальному каналі чи через ЛС модератору."
            ),
            inline=False
        )
        
        embed.add_field(
            name="**7. Заключні положення**",
            value=(
                "7.1 Незнання правил не звільняє від відповідальності.\n"
                "7.2 Адміністрація може змінювати правила у будь-який момент.\n"
                "7.3 Головна мета сервера — комфортне спілкування. Якщо поведінка заважає іншим, адміністрація має право втрутитися навіть без формального порушення."
            ),
            inline=False
        )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)


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
            color=0xc0c0c0
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)


class RulesSetupCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Додаємо persistent views при ініціалізації
        try:
            self.bot.add_view(MainMenuView())
            self.bot.add_view(ServerInfoButtons())
            self.bot.add_view(RolesMenuView())
            self.bot.add_view(ActivityRolesView())
            self.bot.add_view(FAQView())
            self.bot.add_view(RulesDetailsView())
            self.bot.add_view(FinalRulesView())
            self.bot.add_view(GuidesButtons())
            print("✅ All persistent views loaded successfully")
        except Exception as e:
            print(f"❌ Error loading persistent views: {e}")

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

        embed = discord.Embed(color=0xc0c0c0)
        embed.add_field(
            name="```🎀・Ласкаво просимо на сервер!```",
            value=(
                "Раді бачити вас на нашому сервері! Щоб швидко влитися та стати активним учасником, "
                "ознайомтеся з основними розділами сервера за допомогою кнопок нижче. Це допоможе освоїтися, "
                "уникнути порушень і зробити ваше перебування цікавим.\n\n"
                "**Бажаємо приємного проведення часу!**"
            ),
            inline=False
        )

        await ctx.send(embed=embed, view=MainMenuView())


async def setup(bot):
    await bot.add_cog(RulesSetupCommands(bot))