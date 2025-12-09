import asyncio
from datetime import datetime, timedelta
from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from database.database import get_session
from database.crud import get_all_registered_users_for_broadcast

DAYS_OF_WEEK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_days_keyboard_for_update(selected_days: list = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора дней недели (для еженедельного обновления)"""
    if selected_days is None:
        selected_days = []
    
    keyboard = []
    row = []
    for day in DAYS_OF_WEEK:
        prefix = "✅" if day in selected_days else ""
        row.append(InlineKeyboardButton(
            text=f"{prefix} {day}",
            callback_data=f"update_day_{day}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data="update_days_done")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def send_weekly_availability_update(bot: Bot):
    """Отправка еженедельного запроса на обновление доступности"""
    async with get_session() as db:
        users = await get_all_registered_users_for_broadcast(db)
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    "📅 Обновление доступности\n\n"
                    "Пожалуйста, обновите вашу доступность на следующую неделю.\n"
                    "Выберите предпочитаемые дни для работы:\n"
                    "(Нажмите на дни, чтобы выбрать/снять выбор, затем нажмите 'Готово')\n\n"
                    "Или используйте команду /start и выберите 'Обновить доступность'"
                ),
                reply_markup=get_days_keyboard_for_update()
            )
        except Exception as e:
            print(f"Ошибка отправки запроса пользователю {user.telegram_id}: {e}")


async def schedule_weekly_updates(bot: Bot):
    """Планировщик еженедельных обновлений (каждое воскресенье в 10:00)"""
    while True:
        now = datetime.now()
        
        # Вычисляем следующий воскресенье в 10:00
        days_until_sunday = (6 - now.weekday()) % 7
        if days_until_sunday == 0:  # Если сегодня воскресенье
            next_sunday = now.replace(hour=10, minute=0, second=0, microsecond=0)
            if next_sunday <= now:
                next_sunday += timedelta(days=7)
        else:
            next_sunday = now + timedelta(days=days_until_sunday)
            next_sunday = next_sunday.replace(hour=10, minute=0, second=0, microsecond=0)
        
        wait_seconds = (next_sunday - now).total_seconds()
        
        print(f"Следующее обновление доступности: {next_sunday}")
        await asyncio.sleep(wait_seconds)
        
        # Отправляем обновления
        await send_weekly_availability_update(bot)
        
        # Ждём неделю перед следующим запуском
        await asyncio.sleep(60 * 60 * 24 * 7)

