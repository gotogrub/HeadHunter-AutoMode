# HeadHunter Destroyer

Бот для автоматизации работы с HH.ru — автоматическое обновление резюме и массовая рассылка откликов на вакансии.

## Возможности

- **Boost резюме** — автоматическое "обновление" резюме для поднятия в поиске
- **Mass Apply** — массовая рассылка откликов на вакансии по заданным фильтрам
- **Два режима работы:**
  - Desktop Mode — видимый браузер (Windows/Linux с GUI)
  - Server Mode — headless браузер + TUI интерфейс (для SSH/серверов)

## Требования

- Python 3.8+
- Браузер на выбор: Chrome, Edge, Firefox или Chromium

## Установка

### Windows

```batch
pip install -r requirements.txt
playwright install chrome msedge firefox chromium
```

Или просто запустите `install.bat`

### Linux (Kali/Ubuntu/Debian)

```bash
chmod +x install.sh start.sh
./install.sh
```

## Запуск

### Windows (Desktop Mode)

```batch
start.bat
```

или

```batch
python main.py
```

### Linux с GUI

```bash
./start.sh
```

### Linux без GUI (Server Mode)

```bash
# Автоматически определит отсутствие дисплея
./start.sh

# Или принудительно включить server mode
HH_SERVER_MODE=true ./start.sh
```

## Первый запуск и авторизация

1. Запустите бота — откроется браузер
2. Войдите в свой аккаунт HH.ru
3. Нажмите Enter в консоли
4. Сессия сохранится в `browser_data/`

### Авторизация для сервера без GUI

1. Запустите бота на машине с GUI (Windows или Linux Desktop)
2. Авторизуйтесь в браузере
3. Скопируйте папку `browser_data/` на сервер
4. Запустите бота на сервере — он использует сохраненную сессию

## Использование

```
[1] Boost all resumes     — Обновить все резюме
[2] Mass apply            — Откликнуться на вакансии (стандартный поиск)
[3] Mass apply custom     — Откликнуться с настройкой фильтров
[4] Show statistics       — Показать статистику сессии
[5] Manage filters        — Управление фильтрами (blacklist/whitelist)
[6] Export data           — Экспорт данных в CSV
[7] Check login status    — Проверить авторизацию
[8] Clear session         — Очистить сессию (выйти)
[0] Exit                  — Выход
```

### Параметры поиска вакансий

| Параметр | Значения | Описание |
|----------|----------|----------|
| `text` | любой текст | Поисковый запрос |
| `area` | 1, 2, 113... | Регион (1=Москва, 2=СПб, 113=Россия) |
| `experience` | noExperience, between1And3, between3And6, moreThan6 | Опыт работы |
| `schedule` | fullDay, shift, flexible, remote, flyInFlyOut | График работы |
| `salary` | число | Минимальная зарплата |

## Конфигурация

Настройки находятся в `config.py`:

```python
# Режим работы
SERVER_MODE = auto  # auto / true / false
HEADLESS = False    # Скрытый браузер

# Лимиты
LIMITS = {
    "max_responses_per_session": 200,  # Макс. откликов за сессию
    "max_pages_to_scan": 50,           # Макс. страниц поиска
}

# Задержки (секунды)
TIMEOUTS = {
    "between_actions": (2, 5),      # Между действиями
    "between_responses": (3, 8),    # Между откликами
    "resume_update_interval": 240,  # Интервал обновления резюме (мин)
}
```

### Переменные окружения

```bash
HH_SERVER_MODE=true   # Принудительно включить server mode
HH_BROWSER=chrome     # Выбор браузера: chrome, edge, firefox, auto
```

### Выбор браузера

| Значение | Описание |
|----------|----------|
| `auto` | Автоматически: Chrome → Edge (Windows) → Chromium → Firefox |
| `chrome` | Google Chrome |
| `edge` | Microsoft Edge (только Windows) |
| `firefox` | Mozilla Firefox |

Пример запуска с конкретным браузером:

```bash
# Windows
set HH_BROWSER=chrome && python main.py

# Linux
HH_BROWSER=firefox ./start.sh
```

## Структура проекта

```
HeadHunter-Destroyer/
├── main.py              # Точка входа
├── browser.py           # Управление браузером (Chrome/Edge/Firefox)
├── config.py            # Конфигурация
├── database.py          # SQLite база данных
├── filters.py           # Умные фильтры (blacklist/whitelist)
├── resume_booster.py    # Модуль обновления резюме
├── vacancy_applier.py   # Модуль откликов на вакансии
├── tui.py               # Text UI для server mode
├── requirements.txt     # Python зависимости
├── install.bat          # Установщик Windows
├── install.sh           # Установщик Linux
├── start.bat            # Запуск Windows
├── start.sh             # Запуск Linux
├── docs/                # Документация и roadmap
└── browser_data/        # Данные сессии и БД (создается автоматически)
```

## Server Mode (TUI)

В режиме сервера используется библиотека `rich` для красивого отображения в терминале:

```
╭─────────────────── SERVER MODE ───────────────────╮
│  ██╗  ██╗██╗  ██╗    ██████╗ ███████╗███████╗    │
│  ██║  ██║██║  ██║    ██╔══██╗██╔════╝██╔════╝    │
│  ███████║███████║    ██║  ██║█████╗  ███████╗    │
╰───────────────────────────────────────────────────╯

12:34:56 ✓ Python Developer @ Yandex
12:34:58 ~ Senior Dev @ Mail.ru (skipped)
12:35:01 ✓ Backend Developer @ Sber
─── Page 2: found 15 vacancies

┌────────┬─────────────────────────────┐
│ Option │ Description                 │
├────────┼─────────────────────────────┤
│ 1      │ Boost all resumes           │
│ 2      │ Mass apply to vacancies     │
│ 3      │ Mass apply with custom      │
│ 4      │ Show statistics             │
│ 5      │ Check login status          │
│ 0      │ Exit                        │
└────────┴─────────────────────────────┘
```

## Безопасность

- Бот использует случайные задержки между действиями
- Имитирует поведение реального пользователя
- Не хранит пароли — только cookies сессии
- Данные сессии хранятся локально в `browser_data/`

## Ограничения HH.ru

- Обновление резюме: не чаще 1 раза в 4 часа
- Отклики: есть дневной лимит (зависит от аккаунта)
- Бот автоматически учитывает эти ограничения

## Troubleshooting

### Браузер не запускается

```bash
# Linux: установите зависимости
playwright install-deps chromium

# Windows: убедитесь что Edge закрыт
taskkill /f /im msedge.exe
```

### Не работает авторизация

```bash
# Очистите сессию и войдите заново
rm -rf browser_data/
./start.sh
```

### Server mode не определяется

```bash
# Принудительно включите
export HH_SERVER_MODE=true
./start.sh
```

## Лицензия

MIT License

## Disclaimer

Этот инструмент создан для автоматизации рутинных действий при поиске работы. Используйте ответственно и в соответствии с правилами HH.ru.
