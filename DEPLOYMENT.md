# Инструкция по настройке автоматического деплоя

## Обзор

Настроен CI/CD pipeline с использованием GitHub Actions для автоматического деплоя бота на сервер при изменении кода в репозитории.

## Структура файлов

- `.github/workflows/deploy.yml` - Простой workflow для деплоя
- `.github/workflows/deploy-advanced.yml` - Расширенный workflow с тестами и бэкапами
- `deploy.sh` - Скрипт для ручного деплоя

## Настройка GitHub Secrets

Для работы автоматического деплоя необходимо добавить следующие secrets в настройках GitHub репозитория:

**Settings → Secrets and variables → Actions → New repository secret**

### Необходимые Secrets:

1. **SSH_PRIVATE_KEY** - Приватный SSH ключ для подключения к серверу
   ```bash
   # На вашем локальном компьютере или сервере создайте ключ (если еще нет):
   ssh-keygen -t ed25519 -C "github-actions"
   
   # Скопируйте ПРИВАТНЫЙ ключ (id_ed25519):
   cat ~/.ssh/id_ed25519
   ```
   ⚠️ **ВНИМАНИЕ**: Копируйте именно приватный ключ (без `.pub`)

2. **SERVER_HOST** - IP адрес или доменное имя сервера
   ```
   Например: 192.168.1.100 или bot.example.com
   ```

3. **SERVER_USER** - Пользователь для SSH подключения
   ```
   Например: root или deploy
   ```

4. **SERVER_DEPLOY_PATH** - Путь на сервере, куда будет развернут бот
   ```
   Например: /opt/staff-manager-bot или /home/deploy/staff-bot
   ```

## Настройка SSH на сервере

### 1. Добавьте публичный SSH ключ на сервер:

```bash
# На вашем локальном компьютере скопируйте публичный ключ
cat ~/.ssh/id_ed25519.pub

# На сервере добавьте ключ в authorized_keys
mkdir -p ~/.ssh
echo "ваш_публичный_ключ" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
chmod 700 ~/.ssh
```

### 2. Настройте SSH доступ:

Убедитесь, что на сервере разрешен SSH доступ. Проверьте `/etc/ssh/sshd_config`:
```
PubkeyAuthentication yes
PasswordAuthentication no  # Рекомендуется для безопасности
```

### 3. Проверьте подключение:

```bash
ssh SERVER_USER@SERVER_HOST
```

## Настройка на сервере

### 1. Установите Docker и Docker Compose:

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com -o get-docker.sh
sh get-docker.sh
sudo usermod -aG docker $USER

# Установите Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose
```

### 2. Создайте директорию для проекта:

```bash
sudo mkdir -p /opt/staff-manager-bot
sudo chown $USER:$USER /opt/staff-manager-bot
cd /opt/staff-manager-bot
```

### 3. Создайте файл `.env`:

```bash
nano .env
```

Заполните необходимыми значениями (см. `.docker-compose.env.example`):
```env
BOT_TOKEN=ваш_токен
ADMIN_CHAT_IDS=ваш_telegram_id
DATABASE_URL=sqlite+aiosqlite:////app/data/staff_bot.db
WORK_GROUP_ID=
NOTIFICATION_CHANNEL_ID=
```

### 4. Создайте директорию для данных:

```bash
mkdir -p data
chmod 755 data
```

## Выбор workflow

### Простой workflow (deploy.yml)

Используйте, если нужен быстрый деплой без дополнительных проверок:
- Копирование файлов
- Пересборка и перезапуск контейнера
- Базовая проверка статуса

### Расширенный workflow (deploy-advanced.yml)

Используйте для production окружения:
- Проверки линтера (можно добавить тесты)
- Автоматический бэкап базы данных
- Детальная проверка статуса деплоя
- Очистка старых Docker образов

**Для переключения на расширенный workflow:**

1. Переименуйте файлы:
   ```bash
   mv .github/workflows/deploy.yml .github/workflows/deploy-simple.yml
   mv .github/workflows/deploy-advanced.yml .github/workflows/deploy.yml
   ```

2. Или измените имя файла в репозитории через GitHub UI

## Настройка веток

По умолчанию деплой происходит при push в ветку `main`. 

Для изменения ветки отредактируйте `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    branches:
      - main  # Измените на master, develop и т.д.
```

## Ручной деплой

Если нужно выполнить деплой вручную без GitHub Actions:

### 1. Используйте скрипт deploy.sh:

```bash
# Установите права на выполнение
chmod +x deploy.sh

# Установите переменные окружения
export DEPLOY_USER=root
export DEPLOY_HOST=your-server.com
export DEPLOY_PATH=/opt/staff-manager-bot

# Запустите деплой
./deploy.sh
```

### 2. Или вручную:

```bash
# Копирование файлов
rsync -avz --exclude '.env' --exclude 'data' ./ user@server:/opt/staff-manager-bot/

# SSH на сервер
ssh user@server
cd /opt/staff-manager-bot
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Мониторинг деплоя

### Просмотр статуса в GitHub:

1. Перейдите в репозиторий
2. Вкладка **Actions**
3. Выберите нужный workflow run
4. Просмотрите логи выполнения

### Просмотр логов на сервере:

```bash
ssh user@server
cd /opt/staff-manager-bot
docker-compose logs -f
```

## Откат к предыдущей версии

Если что-то пошло не так:

```bash
ssh user@server
cd /opt/staff-manager-bot

# Восстановить из git (если код в git на сервере)
git checkout HEAD~1

# Или восстановить из бэкапа
# (бэкапы находятся в backups/ директории)

# Перезапустить
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Безопасность

### Рекомендации:

1. **Используйте отдельного пользователя для деплоя** (не root):
   ```bash
   sudo useradd -m -s /bin/bash deploy
   sudo usermod -aG docker deploy
   ```

2. **Ограничьте SSH доступ** по IP адресам GitHub Actions:
   ```
   # В /etc/ssh/sshd_config или через firewall
   ```

3. **Не храните .env в Git** - файл должен быть только на сервере

4. **Регулярно обновляйте секреты** SSH ключей

5. **Используйте fail2ban** для защиты от брутфорса:
   ```bash
   sudo apt install fail2ban
   ```

## Решение проблем

### Pipeline не запускается:

- Проверьте, что файл workflow находится в `.github/workflows/`
- Проверьте, что вы пушите в правильную ветку (main)
- Проверьте вкладку Actions в GitHub на наличие ошибок

### Ошибка SSH подключения:

- Проверьте, что SSH_PRIVATE_KEY правильно скопирован (включая начало `-----BEGIN` и конец `-----END`)
- Проверьте, что публичный ключ добавлен на сервер
- Проверьте, что SERVER_USER и SERVER_HOST правильные

### Ошибка на сервере:

- Проверьте логи: `docker-compose logs`
- Проверьте, что .env файл существует и заполнен
- Проверьте права на директории
- Проверьте, что Docker и Docker Compose установлены

## Дополнительные возможности

### Уведомления о деплое в Telegram:

Добавьте в workflow секцию для отправки уведомлений:

```yaml
- name: Send Telegram notification
  if: always()
  uses: appleboy/telegram-action@master
  with:
    to: ${{ secrets.TELEGRAM_CHAT_ID }}
    token: ${{ secrets.TELEGRAM_BOT_TOKEN }}
    message: |
      Deployment ${{ job.status }}!
      Repository: ${{ github.repository }}
      Commit: ${{ github.sha }}
```

Добавьте в Secrets:
- `TELEGRAM_BOT_TOKEN` - токен бота для уведомлений
- `TELEGRAM_CHAT_ID` - ID чата для уведомлений

## Пример полной настройки

1. Создайте SSH ключ: `ssh-keygen -t ed25519`
2. Добавьте публичный ключ на сервер: `ssh-copy-id user@server`
3. Добавьте secrets в GitHub
4. Настройте .env на сервере
5. Сделайте push в main ветку
6. Проверьте деплой в Actions

Готово! Теперь каждый push в main ветку будет автоматически деплоить бота на сервер.

