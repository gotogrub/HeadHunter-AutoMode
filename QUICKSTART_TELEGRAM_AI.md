# Быстрый старт: AI Telegram Помощник

Запусти умного помощника по поиску работы за 5 минут!

## Шаг 1: Создай бота (2 минуты)

1. Открой [@BotFather](https://t.me/BotFather) в Telegram
2. Отправь `/newbot`
3. Придумай название: `My Job Assistant`
4. Придумай username: `my_job_assistant_bot`
5. **Скопируй токен** (выглядит как `123456:ABC-DEF...`)

## Шаг 2: Узнай свой ID (30 секунд)

1. Открой [@userinfobot](https://t.me/userinfobot)
2. **Скопируй свой ID** (число, например `987654321`)

## Шаг 3: Установи зависимости (1 минута)

```bash
pip install python-telegram-bot
```

**Опционально - локальный AI (рекомендуется):**
```bash
# Linux/macOS
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama2
ollama serve  # запусти в отдельном терминале
```

## Шаг 4: Настрой (1 минута)

**Linux/macOS:**
```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
export TELEGRAM_OWNER_ID="987654321"

# Если установил Ollama
export OLLAMA_HOST="http://localhost:11434"
export OLLAMA_MODEL="llama2"
```

**Windows:**
```cmd
set TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
set TELEGRAM_OWNER_ID=987654321

set OLLAMA_HOST=http://localhost:11434
set OLLAMA_MODEL=llama2
```

**Или через .env файл:**
```bash
# Создай .env файл
cat > .env << EOF
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_OWNER_ID=987654321
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2
EOF
```

## Шаг 5: Запусти! (30 секунд)

```bash
# Первый раз - авторизуйся на HH.ru
python main.py
# Войди в браузере, нажми Enter

# Запусти AI бота
python main.py --telegram-ai
```

**Готово!** Открой Telegram и напиши своему боту `/start`

---

## Быстрые примеры

Открой Telegram и попробуй:

```
Ты: /start
Бот: [показывает главное меню с кнопками]

Ты: Найди работу python разработчика
Бот: [ищет и показывает вакансии]

Ты: Покажи мои резюме
Бот: [показывает список резюме с кнопками]

Ты: Какая статистика?
Бот: [показывает статистику откликов с анализом]

Ты: Дай совет
Бот: [анализирует твою статистику и дает рекомендации]
```

---

## Что дальше?

### Используй естественный язык

Не нужно запоминать команды! Просто пиши:

- "Найди вакансии senior python"
- "Обнови резюме"
- "Сколько откликов?"
- "Отправь отклики"
- "Проверь новые ответы"

### Автоматизация

Запусти бота на сервере для работы 24/7:

**Docker:**
```bash
docker-compose up -d
```

**Systemd (Linux):**
```bash
sudo systemctl enable hh-destroyer
sudo systemctl start hh-destroyer
```

### Продвинутые функции

**Несколько аккаунтов:**
```bash
python main.py --telegram-ai --profile work
```

**С AI письмами:**
```bash
export HH_AI_PROVIDER=ollama
python main.py --telegram-ai --ai-letters
```

**Daemon режим (фоновая рассылка):**
```bash
# В отдельном терминале
python main.py --daemon

# И параллельно AI бот
python main.py --telegram-ai
```

---

## Troubleshooting

### Бот не отвечает

**Проверь переменные:**
```bash
echo $TELEGRAM_BOT_TOKEN
echo $TELEGRAM_OWNER_ID
```

Если пусто - установи снова (Шаг 4)

### AI не работает

**Проверь Ollama:**
```bash
curl http://localhost:11434/api/tags
```

Если ошибка - запусти:
```bash
ollama serve
```

### Браузер не открывается

**На сервере без GUI:**
```bash
export HH_SERVER_MODE=true
python main.py --telegram-ai
```

---

## Полная документация

- **Подробный гайд:** [docs/TELEGRAM_AI_BOT.md](docs/TELEGRAM_AI_BOT.md)
- **Deployment:** [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md)
- **README:** [README.md](README.md)

---

## Нужна помощь?

- GitHub Issues: https://github.com/cyberpsychoz/HeadHunter-Destroyer/issues
- Напиши боту: `/help`

**Удачи в поиске работы!** 🚀
