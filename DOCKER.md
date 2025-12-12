# Инструкция по запуску бота в Docker

## Быстрый старт

### 1. Подготовка файлов

1. **Создайте файл `.env`** на основе `.docker-compose.env.example`:
   ```bash
   cp .docker-compose.env.example .env
   ```

   ⚠️ **ВАЖНО**: Убедитесь, что файл `.env` находится в той же директории, что и `docker-compose.yml`!

2. **Заполните необходимые значения в `.env`**:
   - `BOT_TOKEN` - токен бота от @BotFather
   - `ADMIN_CHAT_IDS` - ваш Telegram ID (можно несколько через запятую)
   - `DATABASE_URL` - URL базы данных (по умолчанию SQLite)
   - `WORK_GROUP_ID` и `NOTIFICATION_CHANNEL_ID` (опционально)

### 2. Запуск с Docker Compose (рекомендуется)

```bash
# Сборка и запуск
docker-compose up -d

# Просмотр логов
docker-compose logs -f

# Остановка
docker-compose down

# Перезапуск
docker-compose restart
```

### 3. Запуск без Docker Compose

#### Сборка образа:
```bash
docker build -t staff-manager-bot .
```

#### Запуск контейнера:
```bash
docker run -d \
  --name staff-manager-bot \
  --restart unless-stopped \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  staff-manager-bot
```

#### Просмотр логов:
```bash
docker logs -f staff-manager-bot
```

#### Остановка и удаление:
```bash
docker stop staff-manager-bot
docker rm staff-manager-bot
```

## Структура директорий

После запуска создастся директория `data/` для хранения базы данных SQLite:

```
.
├── data/
│   └── staff_bot.db  # База данных (создается автоматически)
├── .env              # Переменные окружения
├── docker-compose.yml
├── Dockerfile
└── ...
```

## Использование PostgreSQL

Если хотите использовать PostgreSQL вместо SQLite:

1. Создайте файл `docker-compose.postgres.yml`:
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15-alpine
    container_name: staff-bot-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: staff_bot
      POSTGRES_USER: botuser
      POSTGRES_PASSWORD: your_password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  staff-manager-bot:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: staff-manager-bot
    restart: unless-stopped
    env_file:
      - .env
    depends_on:
      - postgres
    volumes:
      - ./data:/app/data

volumes:
  postgres_data:
```

2. Обновите `.env`:
```env
DATABASE_URL=postgresql+asyncpg://botuser:your_password@postgres:5432/staff_bot
```

3. Установите драйвер для PostgreSQL (добавьте в `requirements.txt`):
```
asyncpg==0.29.0
```

4. Запустите:
```bash
docker-compose -f docker-compose.postgres.yml up -d
```

## Управление контейнером

### Просмотр статуса:
```bash
docker-compose ps
# или
docker ps | grep staff-manager-bot
```

### Перезапуск после изменений:
```bash
# Пересобрать образ
docker-compose build

# Перезапустить
docker-compose up -d --force-recreate
```

### Вход в контейнер (для отладки):
```bash
docker exec -it staff-manager-bot /bin/bash
```

### Просмотр логов:
```bash
# Все логи
docker-compose logs

# Последние 100 строк
docker-compose logs --tail=100

# Следить за логами в реальном времени
docker-compose logs -f
```

## Обновление бота

1. Остановите контейнер:
```bash
docker-compose down
```

2. Получите обновленный код (git pull или загрузите новые файлы)

3. Пересоберите образ:
```bash
docker-compose build --no-cache
```

4. Запустите:
```bash
docker-compose up -d
```

## Резервное копирование

### База данных SQLite:
```bash
# Создать резервную копию
docker exec staff-manager-bot cp /app/data/staff_bot.db /app/data/staff_bot.db.backup

# Скопировать на хост
docker cp staff-manager-bot:/app/data/staff_bot.db ./backup/staff_bot_$(date +%Y%m%d_%H%M%S).db
```

### Или напрямую с хоста:
```bash
cp data/staff_bot.db backup/staff_bot_$(date +%Y%m%d_%H%M%S).db
```

## Решение проблем

### Контейнер не запускается:
```bash
# Проверьте логи
docker-compose logs staff-manager-bot

# Проверьте переменные окружения
docker exec staff-manager-bot env | grep BOT
```

### Бот не отвечает:
1. Проверьте токен в `.env`
2. Проверьте логи на ошибки
3. Убедитесь, что контейнер запущен: `docker ps`

### Проблемы с правами доступа:
```bash
# Убедитесь, что директория data доступна для записи
chmod 755 data
```

## Оптимизация для продакшена

1. Используйте `.env` файл с секретными данными
2. Настройте логирование в отдельный файл
3. Используйте PostgreSQL для продакшена
4. Настройте мониторинг и алерты
5. Используйте reverse proxy (nginx) если нужен веб-интерфейс
6. Настройте автоматические резервные копии

## Безопасность

- Никогда не коммитьте `.env` файл в Git
- Используйте сильные пароли для PostgreSQL
- Ограничьте доступ к директории `data/`
- Регулярно обновляйте образы Docker

