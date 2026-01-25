# HeadHunter Destroyer - План развития

## Анализ конкурентов

### Основные проекты

| Проект | Технология | Особенности | Ссылка |
|--------|------------|-------------|--------|
| hh-applicant-tool | Python + API | SQLite база, мультиаккаунт, AI письма, proxy, headless | [GitHub](https://github.com/s3rgeym/hh-applicant-tool) |
| autosend-letters-hh | JS Extension | Шаблоны писем, выбор резюме, авто-подстановка | [GitHub](https://github.com/ia-stepanov/autosend-letters-hh) |
| hh-ru-auto-resume-raising | Python | Автоподъём резюме каждые 4 часа | [GitHub](https://github.com/sergo-code/hh-ru-auto-resume-raising) |
| jojob | Telegram Bot | Управление через Telegram, автоотклики | [Product Radar](https://productradar.ru/product/jojob/) |
| AIHawk | Python + GPT | AI-персонализация откликов для LinkedIn | [GitHub](https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk) |
| EasyApplyJobsBot | Python + Selenium | LinkedIn/Glassdoor, AI ответы на вопросы | [GitHub](https://github.com/wodsuz/EasyApplyJobsBot) |

### Официальные ресурсы

- [HeadHunter API Documentation](https://dev.hh.ru/)
- [HeadHunter API GitHub](https://github.com/hhru/api)

---

## Roadmap

### Фаза 1: Core Improvements (Текущая)

#### 1.1 База данных откликов (SQLite)
- [ ] Создание схемы БД
- [ ] Хранение истории откликов
- [ ] Сохранение контактов работодателей
- [ ] Статистика по компаниям
- [ ] Экспорт в CSV

**Структура таблиц:**
```sql
-- Отклики
CREATE TABLE applications (
    id INTEGER PRIMARY KEY,
    vacancy_id TEXT UNIQUE,
    title TEXT,
    employer TEXT,
    salary TEXT,
    status TEXT,  -- applied, viewed, invited, rejected
    applied_at TIMESTAMP,
    response_at TIMESTAMP
);

-- Компании (blacklist/whitelist)
CREATE TABLE companies (
    id INTEGER PRIMARY KEY,
    name TEXT UNIQUE,
    status TEXT,  -- normal, blacklist, whitelist
    notes TEXT
);

-- Резюме
CREATE TABLE resumes (
    id INTEGER PRIMARY KEY,
    hh_id TEXT UNIQUE,
    title TEXT,
    last_updated TIMESTAMP
);
```

#### 1.2 Умные фильтры
- [ ] Blacklist компаний
- [ ] Blacklist слов в вакансиях
- [ ] Whitelist приоритетных компаний
- [ ] Фильтр по зарплате (мин/макс)
- [ ] Фильтр по дате публикации

**Конфигурация:**
```python
FILTERS = {
    "blacklist_companies": ["Сбербанк", "Тинькофф"],
    "blacklist_words": ["стажёр", "неоплачиваемый", "волонтёр"],
    "whitelist_companies": ["Яндекс", "VK"],
    "min_salary": 150000,
    "max_days_old": 7,
}
```

---

### Фаза 2: AI Integration

#### 2.1 AI-генерация сопроводительных писем
- [ ] Интеграция с OpenAI API
- [ ] Поддержка локальных LLM (Ollama)
- [ ] Шаблоны промптов
- [ ] Кэширование сгенерированных писем

**Пример промпта:**
```
Напиши короткое сопроводительное письмо для вакансии:
Позиция: {title}
Компания: {employer}
Требования: {requirements}

Моё резюме: {resume_summary}

Письмо должно быть на 2-3 предложения, профессиональным тоном.
```

#### 2.2 AI-анализ вакансий
- [ ] Оценка релевантности вакансии (0-100%)
- [ ] Извлечение ключевых требований
- [ ] Автоматический подбор резюме под вакансию

---

### Фаза 3: Telegram Integration

#### 3.1 Telegram Bot
- [ ] Базовые команды управления
- [ ] Уведомления о приглашениях
- [ ] Статистика через бота
- [ ] Inline-кнопки для управления

**Команды:**
```
/start - Начало работы
/status - Статус бота и статистика
/apply <query> - Запустить отклики по запросу
/boost - Обновить все резюме
/stats - Показать статистику
/stop - Остановить текущую задачу
/blacklist <company> - Добавить в черный список
/settings - Настройки
```

#### 3.2 Уведомления
- [ ] Новые приглашения на собеседование
- [ ] Просмотры резюме
- [ ] Ежедневный отчёт

---

### Фаза 4: Automation & Scheduling

#### 4.1 Cron/Systemd интеграция
- [ ] Автоматическое обновление резюме каждые 4 часа
- [ ] Ежедневная рассылка откликов
- [ ] Systemd service файл
- [ ] Docker Compose для деплоя

**Systemd service:**
```ini
[Unit]
Description=HH Destroyer Bot
After=network.target

[Service]
Type=simple
User=hh
WorkingDirectory=/opt/hh-destroyer
ExecStart=/usr/bin/python3 main.py --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

#### 4.2 Мониторинг новых вакансий
- [ ] Парсинг новых вакансий каждые N минут
- [ ] Приоритет свежим вакансиям
- [ ] Webhook уведомления

---

### Фаза 5: Advanced Features

#### 5.1 Мультиаккаунт
- [ ] Несколько профилей HH.ru
- [ ] CLI флаг `--profile`
- [ ] Отдельные настройки для каждого профиля

#### 5.2 Proxy & Anti-detect
- [ ] Ротация User-Agent
- [ ] Поддержка HTTP/SOCKS5 прокси
- [ ] Рандомизация тайминга
- [ ] Browser fingerprint randomization

#### 5.3 Парсинг откликов
- [ ] Сбор ответов работодателей
- [ ] Отслеживание статусов (просмотрено, приглашение, отказ)
- [ ] Автоматическое обновление статусов в БД

#### 5.4 Аналитика
- [ ] Дашборд со статистикой
- [ ] Графики конверсии
- [ ] Топ компаний по ответам
- [ ] Экспорт отчётов

---

## Технические требования

### Для AI функций
- OpenAI API Key ($5-20/месяц) или
- Ollama с локальной моделью (llama2, mistral)

### Для Telegram бота
- Telegram Bot Token (бесплатно, от @BotFather)
- Сервер с постоянным подключением

### Для Proxy
- Список прокси серверов
- Опционально: ротация через API

---

## Приоритеты реализации

1. **[HIGH]** SQLite база данных
2. **[HIGH]** Умные фильтры (blacklist/whitelist)
3. **[MEDIUM]** AI сопроводительные письма
4. **[MEDIUM]** Telegram бот
5. **[MEDIUM]** Cron scheduling
6. **[LOW]** Мультиаккаунт
7. **[LOW]** Proxy support
8. **[LOW]** Аналитический дашборд

---

## Источники и вдохновение

### GitHub проекты
- https://github.com/s3rgeym/hh-applicant-tool
- https://github.com/ia-stepanov/autosend-letters-hh
- https://github.com/sergo-code/hh-ru-auto-resume-raising
- https://github.com/feder-cr/Jobs_Applier_AI_Agent_AIHawk
- https://github.com/wodsuz/EasyApplyJobsBot
- https://github.com/GodsScion/Auto_job_applier_linkedIn

### Документация
- https://dev.hh.ru/
- https://github.com/hhru/api

### Статьи
- https://habr.com/ru/articles/796529/ - Telegram бот для откликов
- https://www.nanohire.ru/blog/ii-poisk-raboty-hh - AI в поиске работы

### Продукты
- https://productradar.ru/product/jojob/ - Telegram бот jojob
