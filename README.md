<div align="center">
  <h1>
        Heroes not die botick
  </h1>
  <p align="center">
    <a href="https://github.com/Kredickoa/disco-bot/stargazers">
      <img src="https://img.shields.io/github/stars/Kredickoa/disco-bot?colorA=363a4f&colorB=b7bdf8&style=for-the-badge" alt="GitHub stars"/>
    </a>
    <a href="https://github.com/Kredickoa/disco-bot/issues">
      <img src="https://img.shields.io/github/issues/Kredickoa/disco-bot?colorA=363a4f&colorB=f5a97f&style=for-the-badge" alt="GitHub issues"/>
    </a>
    <a href="https://github.com/Kredickoa/disco-bot/contributors">
      <img src="https://img.shields.io/github/contributors/Kredickoa/disco-bot?colorA=363a4f&colorB=a6da95&style=for-the-badge" alt="GitHub contributors"/>
    </a>
  </p>
</div>

## Вітаємо!
Це бот спільноти [Heroes not die](https://discord.gg/zAJ7ga5C), створений спеціально для неї, але будь-хто може захостити бота для своєї спільноти 

### Вимоги
- Python - бажано останньої версії

### Встановлення
```bash
pip install -r requirements.txt
```

### Налаштування
- `config.json` - тут знаходяться основні конфігурації бота
- `.env` - тут знаходяться секретні дані, такі як токен бота
> `.env.example` - містить приклад `.env`

### Запуск 
```bash
python run.py
```
 
### Структура проекту
```
src/
├── bot.py              # Основний файл бота
├── commands/           # Команди бота
│   ├── activity/       # Команди активності
│   └── info/          # Інформаційні команди
├── events/            # Події бота
└── modules/           # Допоміжні модулі
```