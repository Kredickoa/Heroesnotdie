const { SlashCommandBuilder, EmbedBuilder, ActionRowBuilder, ButtonBuilder, ButtonStyle, PermissionFlagsBits } = require('discord.js');

// Команда для створення оголошень з кнопками
const setupAnnouncementCommand = {
    data: new SlashCommandBuilder()
        .setName('setup-announcement')
        .setDescription('Створити оголошення з кнопками')
        .addStringOption(option =>
            option.setName('title')
                .setDescription('Заголовок оголошення')
                .setRequired(true))
        .addStringOption(option =>
            option.setName('description')
                .setDescription('Текст оголошення')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('color')
                .setDescription('Колір embed (hex код, наприклад FF1493)')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button1_text')
                .setDescription('Текст першої кнопки')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button1_content')
                .setDescription('Контент першої кнопки (текст або link:посилання)')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button2_text')
                .setDescription('Текст другої кнопки')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button2_content')
                .setDescription('Контент другої кнопки (текст або link:посилання)')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button3_text')
                .setDescription('Текст третьої кнопки')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button3_content')
                .setDescription('Контент третьої кнопки (текст або link:посилання)')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button4_text')
                .setDescription('Текст четвертої кнопки')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('button4_content')
                .setDescription('Контент четвертої кнопки (текст або link:посилання)')
                .setRequired(false))
        .addChannelOption(option =>
            option.setName('channel')
                .setDescription('Канал для відправки (за замовчуванням поточний)')
                .setRequired(false))
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

    async execute(interaction) {
        const title = interaction.options.getString('title');
        const description = interaction.options.getString('description');
        const color = interaction.options.getString('color') || 'FF1493';
        const targetChannel = interaction.options.getChannel('channel') || interaction.channel;

        // Створення embed
        const embed = new EmbedBuilder()
            .setColor(`#${color.replace('#', '')}`)
            .setTitle(title)
            .setTimestamp();

        if (description) {
            embed.setDescription(description);
        }

        // Створення кнопок
        const buttons = new ActionRowBuilder();
        const buttonData = {};

        for (let i = 1; i <= 4; i++) {
            const buttonText = interaction.options.getString(`button${i}_text`);
            const buttonContent = interaction.options.getString(`button${i}_content`);

            if (buttonText) {
                const buttonId = `custom_button_${i}`;
                
                if (buttonContent && buttonContent.startsWith('link:')) {
                    // Кнопка-посилання
                    const link = buttonContent.replace('link:', '');
                    const linkButton = new ButtonBuilder()
                        .setLabel(buttonText)
                        .setStyle(ButtonStyle.Link)
                        .setURL(link);
                    buttons.addComponents(linkButton);
                } else {
                    // Звичайна кнопка
                    const customButton = new ButtonBuilder()
                        .setCustomId(buttonId)
                        .setLabel(buttonText)
                        .setStyle(ButtonStyle.Secondary);
                    buttons.addComponents(customButton);
                    
                    // Зберігаємо контент кнопки
                    buttonData[buttonId] = {
                        text: buttonText,
                        content: buttonContent || `Контент для кнопки "${buttonText}" не налаштовано`
                    };
                }
            }
        }

        // Збереження даних для кнопок
        if (!interaction.client.announcementData) {
            interaction.client.announcementData = new Map();
        }
        
        try {
            const message = await targetChannel.send({
                embeds: [embed],
                components: buttons.components.length > 0 ? [buttons] : []
            });

            // Збереження даних з прив'язкою до повідомлення
            if (Object.keys(buttonData).length > 0) {
                interaction.client.announcementData.set(message.id, buttonData);
            }

            await interaction.reply({
                content: `✅ Оголошення успішно відправлено в ${targetChannel}!`,
                ephemeral: true
            });
        } catch (error) {
            console.error(error);
            await interaction.reply({
                content: '❌ Помилка при відправці оголошення. Перевірте права бота або правильність посилань.',
                ephemeral: true
            });
        }
    },
};

// Команда для додавання кнопок до існуючого повідомлення
const addButtonCommand = {
    data: new SlashCommandBuilder()
        .setName('add-button')
        .setDescription('Додати кнопку до існуючого повідомлення')
        .addStringOption(option =>
            option.setName('message_id')
                .setDescription('ID повідомлення для додавання кнопки')
                .setRequired(true))
        .addStringOption(option =>
            option.setName('button_text')
                .setDescription('Текст кнопки')
                .setRequired(true))
        .addStringOption(option =>
            option.setName('button_content')
                .setDescription('Контент кнопки (текст або link:посилання)')
                .setRequired(true))
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

    async execute(interaction) {
        const messageId = interaction.options.getString('message_id');
        const buttonText = interaction.options.getString('button_text');
        const buttonContent = interaction.options.getString('button_content');

        try {
            const message = await interaction.channel.messages.fetch(messageId);
            
            if (!message) {
                return interaction.reply({
                    content: '❌ Повідомлення не знайдено в цьому каналі.',
                    ephemeral: true
                });
            }

            // Отримання існуючих компонентів
            const existingComponents = message.components[0] || new ActionRowBuilder();
            const newButtons = ActionRowBuilder.from(existingComponents);

            // Перевірка ліміту кнопок (максимум 5)
            if (newButtons.components.length >= 5) {
                return interaction.reply({
                    content: '❌ Досягнуто максимальну кількість кнопок (5) для одного повідомлення.',
                    ephemeral: true
                });
            }

            const buttonId = `custom_button_${Date.now()}`;

            if (buttonContent.startsWith('link:')) {
                // Кнопка-посилання
                const link = buttonContent.replace('link:', '');
                const linkButton = new ButtonBuilder()
                    .setLabel(buttonText)
                    .setStyle(ButtonStyle.Link)
                    .setURL(link);
                newButtons.addComponents(linkButton);
            } else {
                // Звичайна кнопка
                const customButton = new ButtonBuilder()
                    .setCustomId(buttonId)
                    .setLabel(buttonText)
                    .setStyle(ButtonStyle.Secondary);
                newButtons.addComponents(customButton);

                // Збереження даних кнопки
                if (!interaction.client.announcementData) {
                    interaction.client.announcementData = new Map();
                }
                
                const existingData = interaction.client.announcementData.get(messageId) || {};
                existingData[buttonId] = {
                    text: buttonText,
                    content: buttonContent
                };
                interaction.client.announcementData.set(messageId, existingData);
            }

            // Оновлення повідомлення
            await message.edit({
                embeds: message.embeds,
                components: [newButtons]
            });

            await interaction.reply({
                content: `✅ Кнопку "${buttonText}" успішно додано до повідомлення!`,
                ephemeral: true
            });

        } catch (error) {
            console.error(error);
            await interaction.reply({
                content: '❌ Помилка при додаванні кнопки. Перевірте ID повідомлення та права бота.',
                ephemeral: true
            });
        }
    },
};

// Команда для редагування тексту повідомлення
const editAnnouncementCommand = {
    data: new SlashCommandBuilder()
        .setName('edit-announcement')
        .setDescription('Редагувати текст існуючого оголошення')
        .addStringOption(option =>
            option.setName('message_id')
                .setDescription('ID повідомлення для редагування')
                .setRequired(true))
        .addStringOption(option =>
            option.setName('new_title')
                .setDescription('Новий заголовок (залишити пустим щоб не змінювати)')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('new_description')
                .setDescription('Новий опис (залишити пустим щоб не змінювати)')
                .setRequired(false))
        .addStringOption(option =>
            option.setName('new_color')
                .setDescription('Новий колір (hex код)')
                .setRequired(false))
        .setDefaultMemberPermissions(PermissionFlagsBits.Administrator),

    async execute(interaction) {
        const messageId = interaction.options.getString('message_id');
        const newTitle = interaction.options.getString('new_title');
        const newDescription = interaction.options.getString('new_description');
        const newColor = interaction.options.getString('new_color');

        try {
            const message = await interaction.channel.messages.fetch(messageId);
            
            if (!message || message.embeds.length === 0) {
                return interaction.reply({
                    content: '❌ Повідомлення не знайдено або воно не містить embed.',
                    ephemeral: true
                });
            }

            const currentEmbed = message.embeds[0];
            const updatedEmbed = new EmbedBuilder(currentEmbed.toJSON());

            // Оновлення полів якщо вони задані
            if (newTitle) updatedEmbed.setTitle(newTitle);
            if (newDescription !== null) updatedEmbed.setDescription(newDescription || null);
            if (newColor) updatedEmbed.setColor(`#${newColor.replace('#', '')}`);
            
            updatedEmbed.setTimestamp();

            await message.edit({
                embeds: [updatedEmbed],
                components: message.components
            });

            await interaction.reply({
                content: '✅ Оголошення успішно оновлено!',
                ephemeral: true
            });

        } catch (error) {
            console.error(error);
            await interaction.reply({
                content: '❌ Помилка при редагуванні оголошення.',
                ephemeral: true
            });
        }
    },
};

// Обробник натискання кнопок
const handleAnnouncementButtonInteraction = async (interaction) => {
    if (!interaction.isButton()) return;

    const { customId, message } = interaction;
    
    if (!customId.startsWith('custom_button_')) return;

    // Отримання збережених даних
    const buttonData = interaction.client.announcementData?.get(message.id);
    if (!buttonData || !buttonData[customId]) {
        return interaction.reply({
            content: '❌ Дані кнопки не знайдено.',
            ephemeral: true
        });
    }

    const button = buttonData[customId];
    
    // Створення embed з контентом кнопки
    const responseEmbed = new EmbedBuilder()
        .setColor('#FF1493')
        .setTitle(`📄 ${button.text}`)
        .setDescription(button.content)
        .setTimestamp();

    await interaction.reply({
        embeds: [responseEmbed],
        ephemeral: true
    });
};

// Експорт модулів
module.exports = {
    setupAnnouncementCommand,
    addButtonCommand,
    editAnnouncementCommand,
    handleAnnouncementButtonInteraction
};

/*
ПІДСУМОК - ЩО ВМІЄ ЦЕЙ КОД:

📋 КОМАНДИ:
1. /setup-announcement - Створює оголошення з embed та до 4 кнопок
2. /add-button - Додає нову кнопку до існуючого повідомлення
3. /edit-announcement - Редагує заголовок, опис та колір існуючого оголошення

🔘 ТИПИ КНОПОК:
- Текстові кнопки (показують контент в embed при натисканні)
- Кнопки-посилання (відкривають зовнішні посилання)

⚙️ ФУНКЦІЇ:
- Налаштування кольору embed
- Динамічне додавання кнопок до існуючих повідомлень
- Редагування тексту без втрати кнопок
- Зберігання даних кнопок в пам'яті бота
- Приватні відповіді на кнопки (ephemeral)
- Перевірка прав адміністратора

💡 ВИКОРИСТАННЯ:
- Створення інформаційних оголошень
- Інтерактивні повідомлення з додатковою інформацією
- Посилання на зовнішні ресурси через кнопки
- Модульна система - можна легко розширювати
*/

// Приклад використання:
/*
/setup-announcement title:"Новини сервера" 
description:"Важлива інформація для всіх учасників"
button1_text:"Правила" button1_content:"Основні правила сервера..."
button2_text:"Discord" button2_content:"link:https://discord.gg/example"
color:"00FF00"
*/