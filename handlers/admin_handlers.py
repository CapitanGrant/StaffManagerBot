from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from datetime import datetime

from handlers.states import AdminStates
from database.crud import (
    get_all_users, get_active_shifts, create_shift, update_shift, archive_shift,
    get_user_by_telegram_id, update_user_rating, get_all_registered_users_for_broadcast,
    get_setting, set_setting
)
from database.database import get_session
from config import Config
from handlers.user_handlers import get_main_menu_keyboard

router = Router()


def is_admin(user_id: int) -> bool:
    """Проверка прав администратора"""
    return Config.is_admin(user_id) or user_id in Config.ADMIN_CHAT_IDS


@router.message(Command("admin"))
async def admin_menu(message: Message):
    """Главное меню администратора"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        return
    
    keyboard = [
        [InlineKeyboardButton(text="📋 Управление сменами", callback_data="admin_shifts")],
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="⚙️ Настройки системы", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
    ]
    
    await message.answer(
        "🔧 Панель администратора\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )


# ==================== УПРАВЛЕНИЕ СМЕНАМИ ====================

@router.callback_query(F.data == "admin_shifts")
async def admin_shifts_menu(callback: CallbackQuery):
    """Меню управления сменами"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        shifts = await get_active_shifts(db, from_date=datetime.utcnow())
        
        text = "📋 Управление сменами\n\n"
        text += f"Активных смен: {len(shifts)}\n\n"
        
        keyboard = [
            [InlineKeyboardButton(text="➕ Добавить смену", callback_data="admin_add_shift")],
            [InlineKeyboardButton(text="📝 Редактировать смену", callback_data="admin_edit_shift_list")],
            [InlineKeyboardButton(text="👥 Участники смены", callback_data="admin_shift_participants_list")],
            [InlineKeyboardButton(text="✅ Информация о выполненной работе", callback_data="admin_shift_completed_list")],
            [InlineKeyboardButton(text="🗄️ Архивировать смену", callback_data="admin_archive_shift_list")]
        ]
        
        if shifts:
            text += "Ближайшие смены:\n"
            for shift in shifts[:5]:
                date_str = shift.date.strftime("%d.%m.%Y %H:%M")
                text += f"• {date_str}\n"
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data == "admin_add_shift")
async def admin_add_shift_start(callback: CallbackQuery, state: FSMContext):
    """Начало добавления смены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📅 Добавление новой смены\n\n"
        "Введите дату и время смены в формате:\n"
        "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
        "Например: 25.12.2024 14:30"
    )
    await state.set_state(AdminStates.waiting_shift_date)


@router.message(AdminStates.waiting_shift_date)
async def admin_add_shift_date(message: Message, state: FSMContext):
    """Обработка даты смены"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    try:
        # Парсинг даты
        date_str = message.text.strip()
        shift_date = datetime.strptime(date_str, "%d.%m.%Y %H:%M")
        
        if shift_date <= datetime.now():
            await message.answer("❌ Дата должна быть в будущем. Попробуйте снова:")
            return
        
        data = await state.get_data()
        edit_shift_id = data.get("edit_shift_id")
        
        if edit_shift_id:
            # Редактирование существующей смены
            async with get_session() as db:
                shift = await update_shift(db, edit_shift_id, date=shift_date)
                if shift:
                    date_formatted = shift_date.strftime("%d.%m.%Y %H:%M")
                    await message.answer(f"✅ Дата смены успешно изменена на {date_formatted}")
                    await state.clear()
                else:
                    await message.answer("❌ Смена не найдена!")
                    await state.clear()
        else:
            # Добавление новой смены
            await state.update_data(shift_date=shift_date)
            await message.answer("📝 Введите описание смены (или отправьте '-' если описание не требуется):")
            await state.set_state(AdminStates.waiting_shift_description)
    except ValueError:
        await message.answer("❌ Неверный формат даты. Используйте формат ДД.ММ.ГГГГ ЧЧ:ММ\nПопробуйте снова:")


@router.message(AdminStates.waiting_shift_description)
async def admin_add_shift_description(message: Message, state: FSMContext):
    """Завершение добавления или редактирования смены"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    data = await state.get_data()
    edit_shift_id = data.get("edit_shift_id")
    description = message.text if message.text != "-" else None
    
    if edit_shift_id:
        # Редактирование описания существующей смены
        async with get_session() as db:
            shift = await update_shift(db, edit_shift_id, description=description)
            if shift:
                await message.answer(f"✅ Описание смены успешно изменено!")
                await state.clear()
            else:
                await message.answer("❌ Смена не найдена!")
                await state.clear()
    else:
        # Добавление новой смены
        shift_date = data["shift_date"]
        async with get_session() as db:
            shift = await create_shift(db, shift_date, description)
        
        date_str = shift_date.strftime("%d.%m.%Y %H:%M")
        await message.answer(f"✅ Смена успешно добавлена!\n\nДата: {date_str}\nОписание: {description or 'Отсутствует'}")
        await state.clear()


@router.callback_query(F.data == "admin_edit_shift_list")
async def admin_edit_shift_list(callback: CallbackQuery, state: FSMContext):
    """Список смен для редактирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        shifts = await get_active_shifts(db, from_date=datetime.utcnow())
        
        if not shifts:
            await callback.answer("❌ Нет активных смен для редактирования!", show_alert=True)
            return
        
        keyboard = []
        for shift in shifts[:10]:  # Показываем первые 10
            date_str = shift.date.strftime("%d.%m.%Y %H:%M")
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📅 {date_str}",
                    callback_data=f"admin_edit_shift_{shift.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_shifts")])
        
        await callback.message.edit_text(
            "📝 Выберите смену для редактирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("admin_edit_shift_"))
async def admin_edit_shift(callback: CallbackQuery, state: FSMContext):
    """Редактирование смены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    shift_id = int(callback.data.replace("admin_edit_shift_", ""))
    
    async with get_session() as db:
        from database.crud import get_shift_by_id
        shift = await get_shift_by_id(db, shift_id)
        
        if not shift:
            await callback.answer("❌ Смена не найдена!", show_alert=True)
            return
        
        date_str = shift.date.strftime("%d.%m.%Y %H:%M")
        keyboard = [
            [InlineKeyboardButton(text="📅 Изменить дату", callback_data=f"edit_date_{shift_id}")],
            [InlineKeyboardButton(text="📝 Изменить описание", callback_data=f"edit_desc_{shift_id}")],
            [InlineKeyboardButton(text="👥 Участники смены", callback_data=f"admin_participants_{shift_id}")],
            [InlineKeyboardButton(text="✅ Информация о выполненной работе", callback_data=f"admin_completed_{shift_id}")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_edit_shift_list")]
        ]
        
        completed_status = "✅ Добавлена" if shift.completed_info else "❌ Не добавлена"
        await callback.message.edit_text(
            f"📝 Редактирование смены\n\n"
            f"ID: {shift.id}\n"
            f"Дата: {date_str}\n"
            f"Описание: {shift.description or 'Отсутствует'}\n"
            f"Информация о работе: {completed_status}\n\n"
            f"Что вы хотите изменить?",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("edit_date_"))
async def admin_edit_shift_date_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования даты смены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    shift_id = int(callback.data.replace("edit_date_", ""))
    await callback.message.edit_text(
        "📅 Изменение даты смены\n\n"
        "Введите новую дату и время в формате:\n"
        "ДД.ММ.ГГГГ ЧЧ:ММ\n\n"
        "Например: 25.12.2024 14:30"
    )
    await state.set_state(AdminStates.waiting_shift_date)
    await state.update_data(edit_shift_id=shift_id)


@router.callback_query(F.data.startswith("edit_desc_"))
async def admin_edit_shift_desc_start(callback: CallbackQuery, state: FSMContext):
    """Начало редактирования описания смены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    shift_id = int(callback.data.replace("edit_desc_", ""))
    await callback.message.edit_text(
        "📝 Изменение описания смены\n\n"
        "Введите новое описание (или отправьте '-' чтобы удалить описание):"
    )
    await state.set_state(AdminStates.waiting_shift_description)
    await state.update_data(edit_shift_id=shift_id)


@router.callback_query(F.data == "admin_archive_shift_list")
async def admin_archive_shift_list(callback: CallbackQuery):
    """Список смен для архивирования"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        shifts = await get_active_shifts(db)
        
        if not shifts:
            await callback.answer("❌ Нет активных смен для архивирования!", show_alert=True)
            return
        
        keyboard = []
        for shift in shifts[:10]:
            date_str = shift.date.strftime("%d.%m.%Y %H:%M")
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📅 {date_str}",
                    callback_data=f"admin_archive_shift_{shift.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_shifts")])
        
        await callback.message.edit_text(
            "🗄️ Выберите смену для архивирования:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("admin_archive_shift_"))
async def admin_archive_shift(callback: CallbackQuery):
    """Архивирование смены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    shift_id = int(callback.data.replace("admin_archive_shift_", ""))
    
    async with get_session() as db:
        shift = await archive_shift(db, shift_id)
        
        if shift:
            await callback.answer("✅ Смена успешно архивирована!", show_alert=True)
            await admin_shifts_menu(callback)
        else:
            await callback.answer("❌ Смена не найдена!", show_alert=True)


# ==================== УЧАСТНИКИ СМЕНЫ ====================

@router.callback_query(F.data == "admin_shift_participants_list")
async def admin_shift_participants_list(callback: CallbackQuery):
    """Список смен для просмотра участников"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        # Получаем все смены (включая прошедшие) для просмотра участников
        from sqlalchemy import select
        from database.models import Shift
        query = select(Shift).where(Shift.is_active == True).order_by(Shift.date.desc())
        result = await db.execute(query)
        shifts = list(result.scalars().all())
        
        if not shifts:
            await callback.answer("❌ Нет активных смен!", show_alert=True)
            return
        
        keyboard = []
        for shift in shifts[:15]:  # Показываем последние 15 смен
            date_str = shift.date.strftime("%d.%m.%Y %H:%M")
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📅 {date_str}",
                    callback_data=f"admin_participants_{shift.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_shifts")])
        
        await callback.message.edit_text(
            "👥 Выберите смену для просмотра участников:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("admin_participants_"))
async def admin_shift_participants(callback: CallbackQuery):
    """Просмотр участников смены"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    shift_id = int(callback.data.replace("admin_participants_", ""))
    
    async with get_session() as db:
        from database.crud import get_shift_by_id, get_shift_participants
        shift = await get_shift_by_id(db, shift_id)
        
        if not shift:
            await callback.answer("❌ Смена не найдена!", show_alert=True)
            return
        
        participants = await get_shift_participants(db, shift_id)
        date_str = shift.date.strftime("%d.%m.%Y %H:%M")
        
        text = f"👥 Участники смены\n\n"
        text += f"📅 Дата: {date_str}\n"
        text += f"📝 Описание: {shift.description or 'Отсутствует'}\n\n"
        
        if not participants:
            text += "❌ На эту смену нет записанных участников."
        else:
            text += f"Всего участников: {len(participants)}\n\n"
            for i, user in enumerate(participants, 1):
                stars = "⭐" * user.rating
                text += f"{i}. {user.full_name}\n"
                text += f"   📞 Телефон: {user.phone}\n"
                text += f"   ID: {user.telegram_id} | Рейтинг: {stars}\n"
                text += f"   Курс: {user.course} | Опыт: {user.experience_shifts} смен\n\n"
        
        keyboard = [
            [InlineKeyboardButton(text="◀️ Назад к списку", callback_data="admin_shift_participants_list")]
        ]
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


# ==================== ИНФОРМАЦИЯ О ВЫПОЛНЕННОЙ РАБОТЕ ====================

@router.callback_query(F.data == "admin_shift_completed_list")
async def admin_shift_completed_list(callback: CallbackQuery):
    """Список смен для добавления информации о выполненной работе"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        # Получаем все смены (включая прошедшие)
        from sqlalchemy import select
        from database.models import Shift
        query = select(Shift).where(Shift.is_active == True).order_by(Shift.date.desc())
        result = await db.execute(query)
        shifts = list(result.scalars().all())
        
        if not shifts:
            await callback.answer("❌ Нет активных смен!", show_alert=True)
            return
        
        keyboard = []
        for shift in shifts[:15]:  # Показываем последние 15 смен
            date_str = shift.date.strftime("%d.%m.%Y %H:%M")
            has_info = "✅" if shift.completed_info else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{has_info} {date_str}",
                    callback_data=f"admin_completed_{shift.id}"
                )
            ])
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_shifts")])
        
        await callback.message.edit_text(
            "✅ Информация о выполненной работе\n\n"
            "Выберите смену для добавления/просмотра информации:\n"
            "(✅ - информация добавлена, ❌ - не добавлена)",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("admin_completed_"))
async def admin_shift_completed(callback: CallbackQuery, state: FSMContext):
    """Просмотр/редактирование информации о выполненной работе"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    shift_id = int(callback.data.replace("admin_completed_", ""))
    
    async with get_session() as db:
        from database.crud import get_shift_by_id, get_shift_participants
        shift = await get_shift_by_id(db, shift_id)
        
        if not shift:
            await callback.answer("❌ Смена не найдена!", show_alert=True)
            return
        
        participants = await get_shift_participants(db, shift_id)
        date_str = shift.date.strftime("%d.%m.%Y %H:%M")
        
        text = f"✅ Информация о выполненной работе\n\n"
        text += f"📅 Дата: {date_str}\n"
        
        if participants:
            text += f"👥 Участники ({len(participants)}):\n"
            for user in participants:
                text += f"• {user.full_name} ({user.phone})\n"
            text += "\n"
        
        if shift.completed_info:
            text += f"📝 Текущая информация:\n{shift.completed_info}\n\n"
            text += "Введите новую информацию о выполненной работе\n(или отправьте '-' чтобы удалить):"
        else:
            text += "❌ Информация о выполненной работе не добавлена.\n\n"
            text += "Введите информацию о выполненной работе:\n"
            text += "(что было сделано, какие задачи выполнены и т.д.)"
        
        await callback.message.edit_text(text)
        await state.set_state(AdminStates.waiting_completed_info)
        await state.update_data(shift_id=shift_id)


@router.message(AdminStates.waiting_completed_info)
async def admin_shift_completed_info_save(message: Message, state: FSMContext):
    """Сохранение информации о выполненной работе"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    data = await state.get_data()
    shift_id = data["shift_id"]
    
    completed_info = None if message.text == "-" else message.text
    
    async with get_session() as db:
        shift = await update_shift(db, shift_id, completed_info=completed_info)
        
        if shift:
            if completed_info:
                await message.answer("✅ Информация о выполненной работе успешно сохранена!")
            else:
                await message.answer("✅ Информация о выполненной работе удалена!")
        else:
            await message.answer("❌ Смена не найдена!")
    
    await state.clear()


# ==================== УПРАВЛЕНИЕ ПОЛЬЗОВАТЕЛЯМИ ====================

@router.callback_query(F.data == "admin_users")
async def admin_users_menu(callback: CallbackQuery):
    """Меню управления пользователями"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        users = await get_all_users(db, is_registered=True)
        
        text = f"👥 Управление пользователями\n\nВсего зарегистрированных: {len(users)}\n\n"
        
        keyboard = [
            [InlineKeyboardButton(text="📋 Список пользователей", callback_data="admin_users_list")],
            [InlineKeyboardButton(text="⭐ Изменить рейтинг", callback_data="admin_change_rating")]
        ]
        
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: CallbackQuery):
    """Список всех пользователей"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        users = await get_all_users(db, is_registered=True)
        
        if not users:
            await callback.message.edit_text(
                "👥 Нет зарегистрированных пользователей.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
                ])
            )
            return
        
        text = f"👥 Список пользователей (всего: {len(users)})\n\n"
        
        # Показываем первые 20 пользователей
        for i, user in enumerate(users[:20], 1):
            stars = "⭐" * user.rating
            text += f"{i}. {user.full_name}\n"
            text += f"   📞 Телефон: {user.phone}\n"
            text += f"   ID: {user.telegram_id} | Рейтинг: {stars} ({user.rating}/5)\n"
            text += f"   Курс: {user.course} | Смен: {user.experience_shifts}\n\n"
        
        if len(users) > 20:
            text += f"\n... и ещё {len(users) - 20} пользователей"
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
            ])
        )


@router.callback_query(F.data == "admin_change_rating")
async def admin_change_rating_start(callback: CallbackQuery, state: FSMContext):
    """Начало изменения рейтинга"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "⭐ Изменение рейтинга пользователя\n\n"
        "Введите Telegram ID пользователя:"
    )
    await state.set_state(AdminStates.waiting_user_telegram_id)


@router.message(AdminStates.waiting_user_telegram_id)
async def admin_change_rating_user(message: Message, state: FSMContext):
    """Обработка Telegram ID для изменения рейтинга"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    try:
        telegram_id = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректный Telegram ID (число). Попробуйте снова:")
        return
    
    async with get_session() as db:
        user = await get_user_by_telegram_id(db, telegram_id)
        
        if not user:
            await message.answer(f"❌ Пользователь с ID {telegram_id} не найден. Попробуйте снова:")
            return
        
        await state.update_data(telegram_id=telegram_id)
        await message.answer(
            f"👤 Пользователь: {user.full_name}\n"
            f"Текущий рейтинг: {user.rating}/5\n\n"
            f"Введите новый рейтинг (от 1 до 5):"
        )
        await state.set_state(AdminStates.waiting_rating)


@router.message(AdminStates.waiting_rating)
async def admin_change_rating_value(message: Message, state: FSMContext):
    """Завершение изменения рейтинга"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    try:
        rating = int(message.text.strip())
        if not 1 <= rating <= 5:
            await message.answer("❌ Рейтинг должен быть от 1 до 5. Попробуйте снова:")
            return
    except ValueError:
        await message.answer("❌ Введите число от 1 до 5. Попробуйте снова:")
        return
    
    data = await state.get_data()
    telegram_id = data["telegram_id"]
    
    async with get_session() as db:
        user = await update_user_rating(db, telegram_id, rating)
        
        if user:
            await message.answer(
                f"✅ Рейтинг пользователя {user.full_name} успешно изменён!\n"
                f"Новый рейтинг: {rating}/5 ⭐"
            )
        else:
            await message.answer("❌ Не удалось обновить рейтинг.")
    
    await state.clear()


# ==================== НАСТРОЙКИ СИСТЕМЫ ====================

@router.callback_query(F.data == "admin_settings")
async def admin_settings_menu(callback: CallbackQuery):
    """Меню настроек системы"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    async with get_session() as db:
        work_group_id_setting = await get_setting(db, "work_group_id")
        work_group_id = work_group_id_setting if work_group_id_setting else (Config.WORK_GROUP_ID if Config.WORK_GROUP_ID else "Не установлен")
        
        channel_id_setting = await get_setting(db, "notification_channel_id")
        channel_id = channel_id_setting if channel_id_setting else (Config.NOTIFICATION_CHANNEL_ID if Config.NOTIFICATION_CHANNEL_ID else "Не установлен")
        
        admin_ids = ", ".join(map(str, Config.ADMIN_CHAT_IDS)) if Config.ADMIN_CHAT_IDS else "Не установлены"
        
        text = (
            "⚙️ Настройки системы\n\n"
            f"🔹 Admin Chat IDs: {admin_ids}\n"
            f"🔹 Work Group ID: {work_group_id}\n"
            f"🔹 Notification Channel ID: {channel_id}\n\n"
            "Выберите параметр для изменения:"
        )
        
        keyboard = [
            [InlineKeyboardButton(text="💬 Work Group ID", callback_data="admin_set_work_group")],
            [InlineKeyboardButton(text="📢 Notification Channel ID", callback_data="admin_set_channel")]
        ]
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_back")])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data == "admin_set_work_group")
async def admin_set_work_group_start(callback: CallbackQuery, state: FSMContext):
    """Начало установки Work Group ID"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "💬 Установка Work Group ID\n\n"
        "Введите ID рабочего чата (число, можно узнать через @userinfobot):"
    )
    await state.set_state(AdminStates.waiting_setting_value)
    await state.update_data(setting_key="work_group_id")


@router.callback_query(F.data == "admin_set_channel")
async def admin_set_channel_start(callback: CallbackQuery, state: FSMContext):
    """Начало установки Notification Channel ID"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    await callback.message.edit_text(
        "📢 Установка Notification Channel ID\n\n"
        "Введите ID канала уведомлений (число с минусом, можно узнать через @userinfobot):"
    )
    await state.set_state(AdminStates.waiting_setting_value)
    await state.update_data(setting_key="notification_channel_id")


@router.message(AdminStates.waiting_setting_value)
async def admin_set_setting_value(message: Message, state: FSMContext):
    """Обработка значения настройки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    try:
        setting_value = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Введите корректное число. Попробуйте снова:")
        return
    
    data = await state.get_data()
    setting_key = data["setting_key"]
    
    async with get_session() as db:
        await set_setting(db, setting_key, str(setting_value))
    
    setting_name = "Work Group ID" if setting_key == "work_group_id" else "Notification Channel ID"
    await message.answer(f"✅ {setting_name} успешно установлен: {setting_value}")
    await state.clear()


# ==================== РАССЫЛКА ====================

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_start(callback: CallbackQuery, state: FSMContext):
    """Начало рассылки"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    from database.crud import get_setting
    
    async with get_session() as db:
        work_group_id = await get_setting(db, "work_group_id")
        work_group_id = int(work_group_id) if work_group_id else Config.WORK_GROUP_ID
        
        notification_channel_id = await get_setting(db, "notification_channel_id")
        notification_channel_id = int(notification_channel_id) if notification_channel_id else Config.NOTIFICATION_CHANNEL_ID
    
    targets = []
    if work_group_id:
        targets.append(f"Рабочий чат ({work_group_id})")
    if notification_channel_id:
        targets.append(f"Канал уведомлений ({notification_channel_id})")
    
    if not targets:
        await callback.answer("❌ Не настроены Work Group ID или Notification Channel ID!", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"📢 Рассылка сообщения\n\n"
        f"Сообщение будет отправлено в:\n" + "\n".join(f"• {target}" for target in targets) + "\n\n"
        f"Введите текст сообщения для рассылки:"
    )
    await state.set_state(AdminStates.waiting_broadcast_message)


@router.message(AdminStates.waiting_broadcast_message)
async def admin_broadcast_send(message: Message, state: FSMContext):
    """Отправка рассылки"""
    if not is_admin(message.from_user.id):
        await message.answer("❌ У вас нет прав администратора.")
        await state.clear()
        return
    
    broadcast_text = message.text or message.caption
    if not broadcast_text:
        await message.answer("❌ Сообщение не может быть пустым. Попробуйте снова:")
        return
    
    from database.crud import get_setting
    
    async with get_session() as db:
        work_group_id = await get_setting(db, "work_group_id")
        work_group_id = int(work_group_id) if work_group_id else Config.WORK_GROUP_ID
        
        notification_channel_id = await get_setting(db, "notification_channel_id")
        notification_channel_id = int(notification_channel_id) if notification_channel_id else Config.NOTIFICATION_CHANNEL_ID
    
    sent = 0
    failed = 0
    
    targets = []
    if work_group_id:
        targets.append(("группу", work_group_id))
    if notification_channel_id:
        targets.append(("канал", notification_channel_id))
    
    if not targets:
        await message.answer("❌ Не настроены Work Group ID или Notification Channel ID!")
        await state.clear()
        return
    
    status_message = await message.answer(f"📤 Отправка рассылки...")
    
    # Отправляем в каждую цель
    for target_name, target_id in targets:
        try:
            if message.photo:
                await message.bot.send_photo(
                    chat_id=target_id,
                    photo=message.photo[-1].file_id,
                    caption=broadcast_text
                )
            elif message.video:
                await message.bot.send_video(
                    chat_id=target_id,
                    video=message.video.file_id,
                    caption=broadcast_text
                )
            elif message.document:
                await message.bot.send_document(
                    chat_id=target_id,
                    document=message.document.file_id,
                    caption=broadcast_text
                )
            else:
                await message.bot.send_message(
                    chat_id=target_id,
                    text=broadcast_text
                )
            sent += 1
        except Exception as e:
            failed += 1
            print(f"Ошибка отправки в {target_name} ({target_id}): {e}")
    
    await status_message.edit_text(
        f"✅ Рассылка завершена!\n\n"
        f"✅ Отправлено в: {sent}\n"
        f"❌ Ошибок: {failed}\n"
        f"📊 Всего целей: {len(targets)}"
    )
    
    await state.clear()


@router.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Возврат в главное меню администратора"""
    if not is_admin(callback.from_user.id):
        await callback.answer("❌ У вас нет прав администратора.", show_alert=True)
        return
    
    keyboard = [
        [InlineKeyboardButton(text="📋 Управление сменами", callback_data="admin_shifts")],
        [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
        [InlineKeyboardButton(text="⚙️ Настройки системы", callback_data="admin_settings")],
        [InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast")]
    ]
    
    await callback.message.edit_text(
        "🔧 Панель администратора\n\nВыберите раздел:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
    )

