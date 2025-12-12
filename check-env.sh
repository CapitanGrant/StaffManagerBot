#!/bin/bash
# Скрипт для проверки переменных окружения перед запуском Docker

echo "Проверка файла .env..."
if [ ! -f .env ]; then
    echo "❌ ОШИБКА: Файл .env не найден!"
    echo "Создайте файл .env на основе .docker-compose.env.example"
    exit 1
fi

echo "✅ Файл .env найден"
echo ""
echo "Проверка обязательных переменных..."

# Проверяем BOT_TOKEN
if grep -q "BOT_TOKEN=your_bot_token_here" .env || ! grep -q "^BOT_TOKEN=" .env; then
    echo "❌ BOT_TOKEN не установлен или содержит значение по умолчанию"
    exit 1
fi

# Проверяем ADMIN_CHAT_IDS
if ! grep -q "^ADMIN_CHAT_IDS=" .env || [ -z "$(grep "^ADMIN_CHAT_IDS=" .env | cut -d'=' -f2)" ]; then
    echo "⚠️  ADMIN_CHAT_IDS не установлен"
fi

echo "✅ Обязательные переменные проверены"
echo ""
echo "Текущие значения (первые 20 символов):"
grep -E "^(BOT_TOKEN|ADMIN_CHAT_IDS|DATABASE_URL)=" .env | sed 's/\(.\{20\}\).*/\1.../'

