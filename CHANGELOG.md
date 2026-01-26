# Changelog

Все значимые изменения в проекте HeadHunter Destroyer.

Формат основан на [Keep a Changelog](https://keepachangelog.com/ru/1.0.0/),
и проект следует [Semantic Versioning](https://semver.org/lang/ru/).

## [Unreleased]

### Добавлено

#### AI Telegram Помощник 🤖
- **Умный Telegram бот** с пониманием естественного языка
- **Natural Language Processing** - понимает команды на русском и английском
- **Интеллектуальный поиск вакансий** - "найди работу python с зарплатой 200к"
- **Просмотр резюме** - показ и анализ резюме через бота
- **Персональные рекомендации** - AI анализирует статистику и дает советы
- **Контекстный диалог** - бот помнит последние 10 сообщений
- **Интерактивные кнопки** - быстрый доступ к функциям
- **Полная интеграция** - работает со всеми модулями (браузер, база, AI)
- CLI флаг `--telegram-ai` для запуска AI бота
- Поддержка OpenAI и Ollama для обработки команд
- Подробная документация в `docs/TELEGRAM_AI_BOT.md`
- Быстрый старт в `QUICKSTART_TELEGRAM_AI.md`

**Примеры естественных команд:**
- "Найди вакансии senior python в Москве"
- "Покажи мои резюме"
- "Какая статистика откликов?"
- "Дай совет по поиску работы"
- "Отправь отклики на найденные вакансии"

## [2.0.0] - 2026-01-26

### Добавлено

#### Основной функционал
- **Boost резюме** - автоматическое обновление резюме для поднятия в поиске
- **Mass Apply** - массовая рассылка откликов на вакансии
- **Интерактивный режим** - выбор вакансий перед откликом с полной информацией
- **Умные фильтры** - blacklist/whitelist компаний, blacklist слов, фильтр по зарплате
- **SQLite база данных** - хранение истории откликов, компаний, статистики

#### Сопроводительные письма
- Система шаблонов с плейсхолдерами ({company}, {position}, {salary}, {name}, {date})
- Управление шаблонами через меню
- Установка шаблона по умолчанию
- База данных шаблонов с подсчетом использования

#### AI интеграция
- Поддержка OpenAI (GPT-3.5, GPT-4)
- Поддержка локального Ollama (llama2, mistral, gemma)
- Автоматическое определение доступного провайдера
- Кэширование сгенерированных писем
- Переменные окружения для настройки

#### Отслеживание откликов
- Автоматическая проверка статусов откликов на HH.ru
- Отслеживание статусов: applied, viewed, invited, rejected
- Расчет конверсии (view rate, invite rate, reject rate)
- Отображение последних обновлений за 7 дней
- Пагинация страниц откликов
- CLI флаг `--check-responses` для автоматизации

#### Telegram бот
- Удаленное управление через Telegram
- Защита по TELEGRAM_OWNER_ID (только владелец)
- Команды: /boost, /apply, /stats, /blacklist, /whitelist, /filters
- Inline клавиатура для удобного управления
- Уведомления о статусе выполнения

#### CLI автоматизация
- `--boost` - обновить все резюме
- `--apply` - массовая рассылка откликов
- `--apply-query` - поисковый запрос для вакансий
- `--cover-letter` - использовать шаблоны писем
- `--ai-letters` - генерировать письма через AI
- `--daemon` - непрерывный режим работы (цикл 4ч)
- `--telegram` - запуск Telegram бота
- `--profile` - работа с несколькими аккаунтами
- `--check-responses` - проверка статусов откликов
- `--browser` - выбор браузера (chrome, edge, firefox, auto)
- `--max-apply` - лимит откликов

#### Мультиаккаунт
- Поддержка нескольких профилей HH.ru
- Отдельные директории для каждого профиля
- Изолированные базы данных и логи
- Переменная окружения HH_PROFILE
- Одновременная работа с разными аккаунтами

#### Deployment
- **Docker** - Dockerfile и docker-compose.yml
- **Systemd** - service файл для Linux
- **Ollama integration** - контейнер с локальной LLM
- Переменные окружения через .env
- Подробная документация в DEPLOYMENT.md

#### Логирование
- Структурированные логи в browser_data/logs/
- CSV лог действий для анализа
- Сессионные логи с timestamp
- Логирование всех операций
- Уровни: debug, info, warning, error

#### Статистика
- Общая статистика по откликам
- Статистика по дням и неделям
- Разбивка по статусам
- Конверсия откликов (проценты)
- Топ компаний (blacklist/whitelist)
- Экспорт в CSV

#### Браузеры
- Поддержка Chrome, Edge, Firefox, Chromium
- Автоматический выбор доступного браузера
- Persistent context с сохранением cookies
- Anti-detection (отключение webdriver флагов)
- Headless режим для серверов

#### Server Mode
- TUI интерфейс через Rich library
- Автоматическое определение headless окружения
- Переменная HH_SERVER_MODE
- Красивое отображение прогресса
- ASCII art баннер

#### Интерфейс
- Полностью на русском языке
- Цветной вывод через Colorama
- Эмодзи для статусов
- Прогресс-бары
- Интерактивные меню
- Форматирование зарплат

### Технические улучшения

- Исправлен бесконечный цикл при закрытии (shutdown_in_progress flag)
- Браузер остается открытым между операциями
- Правильные URLs для резюме (https://)
- Debug логирование для troubleshooting
- Graceful shutdown с очисткой ресурсов
- Signal handlers для Ctrl+C
- Обработка ошибок Playwright
- Рандомизированные задержки между действиями
- Проверка авторизации перед операциями

### Документация

- **README.md** - основная документация на русском
- **DEVELOPMENT.md** - roadmap и план развития
- **DEPLOYMENT.md** - инструкции по развертыванию
- **.env.example** - пример конфигурации
- Установочные скрипты (install.sh, install.bat)
- Запускаемые скрипты (start.sh, start.bat)

### Структура проекта

```
HeadHunter-Destroyer/
├── main.py              # Точка входа + CLI + интерактивный режим
├── browser.py           # Управление браузером (Chrome/Edge/Firefox)
├── config.py            # Конфигурация и настройки
├── database.py          # SQLite база данных
├── filters.py           # Умные фильтры (blacklist/whitelist)
├── cover_letters.py     # Шаблоны сопроводительных писем
├── ai_assistant.py      # AI-генерация писем (OpenAI/Ollama)
├── telegram_bot.py      # Telegram бот для удаленного управления
├── response_tracker.py  # Отслеживание статусов откликов
├── logger.py            # Система логирования
├── resume_booster.py    # Модуль обновления резюме
├── vacancy_applier.py   # Модуль откликов на вакансии
├── tui.py               # Text UI для server mode
├── requirements.txt     # Python зависимости
├── Dockerfile           # Контейнеризация
├── docker-compose.yml   # Docker Compose setup
├── hh-destroyer.service # Systemd service
├── .env.example         # Пример переменных окружения
├── install.bat          # Установщик Windows
├── install.sh           # Установщик Linux
├── start.bat            # Запуск Windows
├── start.sh             # Запуск Linux
├── docs/
│   ├── DEVELOPMENT.md   # Roadmap и план развития
│   └── DEPLOYMENT.md    # Deployment guide
└── browser_data/        # Данные сессии (создается автоматически)
    ├── hh_destroyer.db  # SQLite база
    └── logs/            # Логи
```

## Реализованные фазы из DEVELOPMENT.md

### ✅ Phase 1: Core Improvements
- [x] SQLite database
- [x] Smart filters (blacklist/whitelist)
- [x] Salary filters
- [x] Export to CSV
- [x] Statistics

### ✅ Phase 2: AI Integration
- [x] OpenAI integration
- [x] Ollama (local LLM)
- [x] Prompt templates
- [x] Letter caching

### ✅ Phase 3: Telegram Integration
- [x] Basic commands
- [x] Inline buttons
- [x] Statistics via bot
- [x] Owner ID security

### ✅ Phase 4: Automation & Scheduling
- [x] CLI automation
- [x] Daemon mode
- [x] Systemd service
- [x] Docker Compose
- [x] Cron examples

### ⚠️ Phase 5: Advanced Features (Partial)
- [x] Multi-account support
- [x] Response tracking
- [x] Conversion statistics
- [ ] Proxy support (not implemented)
- [ ] Analytics dashboard (not implemented)

## Не реализовано

Функции с низким приоритетом, которые не были реализованы:

1. **Proxy support** - ротация прокси для обхода ограничений
2. **Analytics dashboard** - веб-интерфейс для просмотра статистики
3. **Browser fingerprint randomization** - дополнительная анти-детекция

Эти функции могут быть добавлены в будущих версиях по запросу.

## Зависимости

```
playwright>=1.40.0
colorama>=0.4.6
python-telegram-bot>=20.7 (опционально)
openai>=1.6.0 (опционально)
requests>=2.31.0 (для Ollama)
rich>=13.7.0 (для TUI)
```

## Системные требования

- Python 3.8+
- Chrome/Edge/Firefox/Chromium
- 2GB RAM (минимум)
- 1GB свободного места

## Переменные окружения

```bash
# Режим
HH_SERVER_MODE=true          # Headless режим
HH_BROWSER=auto              # Выбор браузера

# Telegram
TELEGRAM_BOT_TOKEN=...       # Токен бота
TELEGRAM_OWNER_ID=...        # ID владельца

# AI - Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama2

# AI - OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-3.5-turbo

# Профили
HH_PROFILE=work              # Мультиаккаунт
```

## Лицензия

MIT License

## Благодарности

- [HH.ru API Documentation](https://dev.hh.ru/)
- Вдохновлено проектами: hh-applicant-tool, AIHawk, EasyApplyJobsBot
- Построено с использованием Playwright, SQLite, Python

---

**Примечание:** Этот инструмент создан для автоматизации рутинных действий при поиске работы. Используйте ответственно и в соответствии с правилами HH.ru.
