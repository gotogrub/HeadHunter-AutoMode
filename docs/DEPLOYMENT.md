# Развертывание HeadHunter Destroyer

Инструкции по развертыванию бота на сервере в различных режимах.

## Содержание

- [Systemd Service (Linux)](#systemd-service-linux)
- [Docker Compose](#docker-compose)
- [Cron Jobs](#cron-jobs)
- [Переменные окружения](#переменные-окружения)

---

## Systemd Service (Linux)

### Установка

1. **Подготовка пользователя и директорий**

```bash
# Создать пользователя
sudo useradd -r -s /bin/false hh

# Создать директорию
sudo mkdir -p /opt/hh-destroyer
sudo chown hh:hh /opt/hh-destroyer

# Создать директорию для логов
sudo mkdir -p /var/log/hh-destroyer
sudo chown hh:hh /var/log/hh-destroyer
```

2. **Копирование файлов**

```bash
# Копировать код
sudo cp -r * /opt/hh-destroyer/
sudo chown -R hh:hh /opt/hh-destroyer

# Установить зависимости
cd /opt/hh-destroyer
sudo -u hh python3 -m venv venv
sudo -u hh venv/bin/pip install -r requirements.txt
sudo -u hh venv/bin/playwright install chromium
```

3. **Авторизация на HH.ru**

```bash
# Запустить локально с GUI для авторизации
python main.py

# После авторизации скопировать browser_data на сервер
scp -r browser_data/ user@server:/opt/hh-destroyer/
```

4. **Установка службы**

```bash
# Копировать service файл
sudo cp hh-destroyer.service /etc/systemd/system/

# Редактировать переменные окружения
sudo nano /etc/systemd/system/hh-destroyer.service

# Перезагрузить systemd
sudo systemctl daemon-reload

# Запустить службу
sudo systemctl start hh-destroyer

# Проверить статус
sudo systemctl status hh-destroyer

# Включить автозапуск
sudo systemctl enable hh-destroyer
```

5. **Просмотр логов**

```bash
# Логи systemd
sudo journalctl -u hh-destroyer -f

# Логи приложения
tail -f /var/log/hh-destroyer/output.log
tail -f /var/log/hh-destroyer/error.log
```

### Управление

```bash
# Запуск
sudo systemctl start hh-destroyer

# Остановка
sudo systemctl stop hh-destroyer

# Перезапуск
sudo systemctl restart hh-destroyer

# Статус
sudo systemctl status hh-destroyer

# Отключить автозапуск
sudo systemctl disable hh-destroyer
```

---

## Docker Compose

### Требования

- Docker 20.10+
- Docker Compose 2.0+

### Быстрый старт

1. **Авторизация (локально)**

```bash
# Запустить локально для авторизации
python main.py

# browser_data/ будет создана автоматически
```

2. **Настройка переменных**

```bash
# Скопировать пример
cp .env.example .env

# Редактировать
nano .env
```

Пример `.env`:

```bash
# Telegram (опционально)
TELEGRAM_BOT_TOKEN=123456:ABC-DEF...
TELEGRAM_OWNER_ID=987654321

# AI - Ollama (локальный, рекомендуется)
OLLAMA_HOST=http://ollama:11434
OLLAMA_MODEL=llama2

# AI - OpenAI (платный)
# OPENAI_API_KEY=sk-...
# OPENAI_MODEL=gpt-3.5-turbo
```

3. **Запуск**

```bash
# Собрать и запустить
docker-compose up -d

# Просмотр логов
docker-compose logs -f hh-destroyer

# Остановка
docker-compose down
```

### Без Ollama

Если не нужна AI-генерация писем:

```bash
# Убрать Ollama из docker-compose.yml
docker-compose up -d hh-destroyer
```

Или использовать упрощенную версию:

```yaml
version: '3.8'

services:
  hh-destroyer:
    build: .
    container_name: hh-destroyer
    restart: unless-stopped
    volumes:
      - ./browser_data:/app/browser_data
      - ./logs:/app/logs
    command: python main.py --daemon --browser chromium
```

### Обновление

```bash
# Получить обновления
git pull

# Пересобрать контейнеры
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

---

## Cron Jobs

Для тех, кто не хочет daemon режим, можно использовать cron.

### Настройка

```bash
# Открыть crontab
crontab -e
```

### Примеры задач

```bash
# Обновлять резюме каждые 4 часа
0 */4 * * * cd /opt/hh-destroyer && python main.py --boost >> /var/log/hh-destroyer/cron.log 2>&1

# Рассылка каждое утро в 9:00 (макс 50 откликов)
0 9 * * * cd /opt/hh-destroyer && python main.py --apply --max-apply 50 >> /var/log/hh-destroyer/cron.log 2>&1

# Рассылка с AI письмами и поисковым запросом
0 9 * * 1-5 cd /opt/hh-destroyer && python main.py --apply --apply-query "python developer" --ai-letters --max-apply 100 >> /var/log/hh-destroyer/cron.log 2>&1

# Обновление резюме + рассылка (комбо)
0 9,13,17 * * * cd /opt/hh-destroyer && python main.py --boost && python main.py --apply --cover-letter --max-apply 30 >> /var/log/hh-destroyer/cron.log 2>&1
```

### Расписание cron

Формат: `минута час день_месяца месяц день_недели команда`

Примеры:
- `0 */4 * * *` - каждые 4 часа
- `0 9 * * *` - каждый день в 9:00
- `0 9 * * 1-5` - пн-пт в 9:00
- `*/30 * * * *` - каждые 30 минут
- `0 9,13,17 * * *` - в 9:00, 13:00, 17:00

---

## Переменные окружения

### Основные

| Переменная | Значение | Описание |
|------------|----------|----------|
| `HH_SERVER_MODE` | `true`/`false` | Headless режим без GUI |
| `HH_BROWSER` | `chrome`/`edge`/`firefox`/`auto` | Выбор браузера |

### Telegram Bot

| Переменная | Значение | Описание |
|------------|----------|----------|
| `TELEGRAM_BOT_TOKEN` | `123456:ABC-DEF...` | Токен от @BotFather |
| `TELEGRAM_OWNER_ID` | `987654321` | Ваш Telegram ID |

Получить токен:
1. Написать [@BotFather](https://t.me/BotFather)
2. `/newbot`
3. Скопировать токен

Узнать свой ID:
1. Написать [@userinfobot](https://t.me/userinfobot)
2. Скопировать ID

### AI - Ollama (Локальный)

| Переменная | Значение | Описание |
|------------|----------|----------|
| `HH_AI_PROVIDER` | `ollama` | Использовать Ollama |
| `OLLAMA_HOST` | `http://localhost:11434` | URL Ollama |
| `OLLAMA_MODEL` | `llama2`/`mistral`/`gemma` | Модель LLM |

Установка Ollama:
```bash
# Linux
curl -fsSL https://ollama.com/install.sh | sh

# Запуск
ollama serve

# Скачать модель
ollama pull llama2
```

### AI - OpenAI

| Переменная | Значение | Описание |
|------------|----------|----------|
| `HH_AI_PROVIDER` | `openai` | Использовать OpenAI |
| `OPENAI_API_KEY` | `sk-...` | API ключ OpenAI |
| `OPENAI_MODEL` | `gpt-3.5-turbo` | Модель GPT |

Получить ключ:
1. Перейти на [platform.openai.com](https://platform.openai.com)
2. API Keys → Create new secret key

---

## Мониторинг

### Логи приложения

```bash
# Systemd
tail -f /var/log/hh-destroyer/output.log

# Docker
docker-compose logs -f hh-destroyer

# Логи базы данных
ls -lh browser_data/logs/
```

### Статистика

```bash
# Через CLI
python main.py
# Выбрать [4] Показать статистику

# Через Telegram
/stats
```

### Проверка здоровья

```bash
# Systemd
sudo systemctl status hh-destroyer

# Docker
docker-compose ps
docker stats hh-destroyer
```

---

## Troubleshooting

### Systemd служба не запускается

```bash
# Проверить логи
sudo journalctl -u hh-destroyer -n 50

# Проверить права
sudo chown -R hh:hh /opt/hh-destroyer

# Проверить путь к Python
which python3
# Обновить ExecStart в service файле
```

### Docker контейнер падает

```bash
# Проверить логи
docker-compose logs hh-destroyer

# Проверить авторизацию
ls -la browser_data/

# Пересобрать
docker-compose down
docker-compose build --no-cache
docker-compose up
```

### Браузер не запускается в headless

```bash
# Установить зависимости
playwright install-deps chromium

# Проверить переменную
echo $HH_SERVER_MODE

# Принудительно включить
export HH_SERVER_MODE=true
```

---

## Безопасность

### Рекомендации

1. **Не коммитить секреты**
   ```bash
   # Добавить в .gitignore
   echo ".env" >> .gitignore
   echo "browser_data/" >> .gitignore
   ```

2. **Ограничить доступ к файлам**
   ```bash
   chmod 600 .env
   chmod 700 browser_data/
   ```

3. **Использовать firewall**
   ```bash
   # Заблокировать внешний доступ к Ollama
   sudo ufw deny 11434
   ```

4. **Регулярные обновления**
   ```bash
   git pull
   pip install -r requirements.txt --upgrade
   ```

---

## Backup

### Что бэкапить

- `browser_data/` - сессия, БД, логи
- `.env` - переменные окружения
- Конфигурационные файлы

### Пример backup скрипта

```bash
#!/bin/bash
BACKUP_DIR="/backup/hh-destroyer"
DATE=$(date +%Y%m%d_%H%M%S)

# Создать backup
tar -czf $BACKUP_DIR/backup_$DATE.tar.gz \
  browser_data/ \
  .env \
  hh-destroyer.service

# Удалить старые (>30 дней)
find $BACKUP_DIR -name "backup_*.tar.gz" -mtime +30 -delete
```

Добавить в cron:
```bash
0 3 * * * /opt/hh-destroyer/backup.sh
```

---

## Масштабирование

### Несколько аккаунтов

```bash
# Создать отдельные директории
/opt/hh-destroyer-account1/
/opt/hh-destroyer-account2/

# Создать отдельные службы
hh-destroyer-account1.service
hh-destroyer-account2.service
```

### Load balancing

Для большого количества откликов можно запустить несколько инстансов:

```yaml
services:
  hh-destroyer-1:
    build: .
    volumes:
      - ./browser_data_1:/app/browser_data
    command: python main.py --daemon --max-apply 50

  hh-destroyer-2:
    build: .
    volumes:
      - ./browser_data_2:/app/browser_data
    command: python main.py --daemon --max-apply 50
```
