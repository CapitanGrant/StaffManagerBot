#!/bin/bash
# Скрипт для ручного деплоя на сервер
# Использование: ./deploy.sh

set -e

# Цвета для вывода
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Настройки (замените на свои)
SERVER_USER="${DEPLOY_USER:-root}"
SERVER_HOST="${DEPLOY_HOST:-your-server.com}"
SERVER_PATH="${DEPLOY_PATH:-/opt/staff-manager-bot}"

echo -e "${GREEN}=== Staff Manager Bot Deployment ===${NC}"
echo ""

# Проверка SSH ключа
if [ ! -f ~/.ssh/id_rsa ] && [ ! -f ~/.ssh/id_ed25519 ]; then
    echo -e "${RED}❌ SSH ключ не найден!${NC}"
    echo "Создайте SSH ключ: ssh-keygen -t ed25519 -C 'your_email@example.com'"
    exit 1
fi

# Проверка .env файла
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠️  Файл .env не найден локально${NC}"
    echo "Убедитесь, что .env файл существует на сервере"
fi

echo "Сервер: ${SERVER_USER}@${SERVER_HOST}"
echo "Путь: ${SERVER_PATH}"
echo ""

# Подтверждение
read -p "Продолжить деплой? (y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    exit 1
fi

# Создание директории на сервере
echo -e "${YELLOW}=== Создание директории на сервере ===${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} "mkdir -p ${SERVER_PATH}/data"

# Копирование файлов
echo -e "${YELLOW}=== Копирование файлов ===${NC}"
rsync -avz --delete \
    --exclude '.env' \
    --exclude '.git' \
    --exclude 'data' \
    --exclude '__pycache__' \
    --exclude '*.pyc' \
    --exclude '.venv' \
    --exclude 'venv' \
    --exclude '*.db' \
    --exclude '*.sqlite' \
    ./ ${SERVER_USER}@${SERVER_HOST}:${SERVER_PATH}/

# Бэкап базы данных
echo -e "${YELLOW}=== Создание бэкапа БД ===${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} << EOF
    cd ${SERVER_PATH}
    if [ -f "data/staff_bot.db" ]; then
        BACKUP_DIR="backups/\$(date +%Y%m%d_%H%M%S)"
        mkdir -p "\$BACKUP_DIR"
        cp data/staff_bot.db "\$BACKUP_DIR/staff_bot.db"
        echo "✅ Бэкап создан: \$BACKUP_DIR/staff_bot.db"
    fi
EOF

# Деплой
echo -e "${YELLOW}=== Деплой на сервере ===${NC}"
ssh ${SERVER_USER}@${SERVER_HOST} << EOF
    set -e
    cd ${SERVER_PATH}
    
    echo "Остановка контейнера..."
    docker-compose down || true
    
    echo "Сборка образа..."
    docker-compose build --no-cache
    
    echo "Запуск контейнера..."
    docker-compose up -d
    
    echo "Ожидание запуска..."
    sleep 10
    
    echo "Проверка статуса..."
    docker-compose ps
    
    echo "Последние логи:"
    docker-compose logs --tail=50
EOF

echo ""
echo -e "${GREEN}✅ Деплой завершен успешно!${NC}"
echo ""
echo "Для просмотра логов:"
echo "  ssh ${SERVER_USER}@${SERVER_HOST} 'cd ${SERVER_PATH} && docker-compose logs -f'"

