# Используем официальный Python образ
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (если нужны)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем Python зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь код приложения
COPY . .

# Создаем директорию для базы данных (если используется SQLite)
RUN mkdir -p /app/data && \
    chmod 755 /app/data

# Создаем непривилегированного пользователя для безопасности
RUN useradd -m -u 1000 botuser && \
    chown -R botuser:botuser /app

# Переключаемся на непривилегированного пользователя
USER botuser

# Переменные окружения по умолчанию (можно переопределить через docker run -e или .env)
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Открываем порт (если нужно для мониторинга/здоровья, можно удалить если не используется)
# EXPOSE 8000

# Команда запуска
CMD ["python", "main.py"]

