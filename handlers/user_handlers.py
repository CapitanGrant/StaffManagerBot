from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from datetime import datetime
from typing import Optional

from handlers.states import OnboardingStates, UpdateAvailabilityStates
from handlers.validators import validate_phone, validate_course, validate_experience, parse_preferred_days
from database.crud import (
    get_user_by_telegram_id, create_user, update_user,
    get_all_registered_users_for_broadcast, get_user_shifts,
    get_active_shifts, assign_user_to_shift, cancel_shift_assignment,
    update_user_rating
)
from database.database import get_session
from config import Config
import asyncio

router = Router()

DAYS_OF_WEEK = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]


def get_main_menu_keyboard() -> InlineKeyboardMarkup:
    """Клавиатура главного меню"""
    keyboard = [
        [InlineKeyboardButton(text="📋 Просмотр доступных смен", callback_data="view_shifts")],
        [InlineKeyboardButton(text="📝 Мои записи", callback_data="my_shifts")],
        [InlineKeyboardButton(text="🔄 Обновить доступность", callback_data="update_availability")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_days_keyboard(selected_days: list = None) -> InlineKeyboardMarkup:
    """Клавиатура для выбора дней недели"""
    if selected_days is None:
        selected_days = []

    keyboard = []
    row = []
    for day in DAYS_OF_WEEK:
        prefix = "✅" if day in selected_days else ""
        row.append(InlineKeyboardButton(
            text=f"{prefix} {day}",
            callback_data=f"day_{day}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([InlineKeyboardButton(text="✅ Готово", callback_data="days_done")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


async def add_user_to_groups(bot, telegram_id: int):
    """Автоматическое добавление пользователя в группы после регистрации"""
    try:
        from database.crud import get_setting

        async with get_session() as db:
            # Получаем ID из настроек БД или из конфига
            notification_channel_id = await get_setting(db, "notification_channel_id")
            notification_channel_id = int(notification_channel_id) if notification_channel_id else Config.NOTIFICATION_CHANNEL_ID

            work_group_id = await get_setting(db, "work_group_id")
            work_group_id = int(work_group_id) if work_group_id else Config.WORK_GROUP_ID

        # Добавление в канал уведомлений
        if notification_channel_id:
            try:
                await bot.get_chat_member(notification_channel_id, telegram_id)
            except:
                # Если пользователь не в канале, попробуем добавить
                try:
                    await bot.ban_chat_member(notification_channel_id, telegram_id)
                    await bot.unban_chat_member(notification_channel_id, telegram_id)
                except Exception as e:
                    print(f"Ошибка при добавлении в канал: {e}")

        # Добавление в рабочий чат
        if work_group_id:
            try:
                await bot.get_chat_member(work_group_id, telegram_id)
            except:
                # Если пользователь не в группе, приглашаем
                try:
                    invite_link = await bot.create_chat_invite_link(work_group_id, member_limit=1)
                    await bot.send_message(
                        chat_id=telegram_id,
                        text=f"🎉 Добро пожаловать! Присоединяйтесь к рабочему чату:\n{invite_link.invite_link}"
                    )
                except Exception as e:
                    print(f"Ошибка при добавлении в группу: {e}")
    except Exception as e:
        print(f"Ошибка при добавлении пользователя в группы: {e}")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    """Обработка команды /start"""
    await state.clear()
    async with get_session() as db:
        user = await get_user_by_telegram_id(db, message.from_user.id)

        if user and user.is_registered:
            await message.answer(
                "👋 Добро пожаловать обратно!\n\n"
                "Выберите действие:",
                reply_markup=get_main_menu_keyboard()
            )
        else:
            await message.answer(
                "👋 Добро пожаловать в бота управления сменами!\n\n"
                "Для начала работы необходимо пройти регистрацию.\n"
                "Пожалуйста, укажите ваше ФИО полностью:"
            )
            await state.set_state(OnboardingStates.full_name)


@router.message(OnboardingStates.full_name)
async def process_full_name(message: Message, state: FSMContext):
    """Обработка ФИО"""
    if len(message.text) < 3:
        await message.answer("❌ ФИО должно содержать хотя бы 3 символа. Попробуйте снова:")
        return

    await state.update_data(full_name=message.text)
    await message.answer("📝 Укажите ваши навыки (1. Сборка \n2. Упаковка\n3. Опресовка\n4. Ремонт):")
    await state.set_state(OnboardingStates.skills)


@router.message(OnboardingStates.skills)
async def process_skills(message: Message, state: FSMContext):
    """Обработка навыков"""
    await state.update_data(skills=message.text)
    await message.answer("💼 Укажите количество отработанных смен (целое число):")
    await state.set_state(OnboardingStates.experience_shifts)


@router.message(OnboardingStates.experience_shifts)
async def process_experience(message: Message, state: FSMContext):
    """Обработка опыта"""
    experience = validate_experience(message.text)
    if experience is None:
        await message.answer("❌ Введите корректное целое число (0 или больше). Попробуйте снова:")
        return

    await state.update_data(experience_shifts=experience)
    await message.answer("🎓 Укажите ваш курс обучения (число от 1 до 5):")
    await state.set_state(OnboardingStates.course)


@router.message(OnboardingStates.course)
async def process_course(message: Message, state: FSMContext):
    """Обработка курса"""
    course = validate_course(message.text)
    if course is None:
        await message.answer("❌ Курс должен быть числом от 1 до 5. Попробуйте снова:")
        return

    await state.update_data(course=course)
    await message.answer("📞 Укажите ваш контактный телефон:")
    await state.set_state(OnboardingStates.phone)


@router.message(OnboardingStates.phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка телефона"""
    if not validate_phone(message.text):
        await message.answer("❌ Некорректный формат телефона. Попробуйте снова:")
        return

    await state.update_data(phone=message.text)
    await message.answer(
        "📅 Выберите предпочитаемые дни для работы:\n"
        "(Нажмите на дни, чтобы выбрать/снять выбор, затем нажмите 'Готово')",
        reply_markup=get_days_keyboard()
    )
    await state.set_state(OnboardingStates.preferred_days)
    await state.update_data(selected_days=[])


@router.callback_query(OnboardingStates.preferred_days, F.data.startswith("day_"))
async def process_day_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня недели"""
    day = callback.data.replace("day_", "")
    data = await state.get_data()
    selected_days = data.get("selected_days", [])

    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.append(day)

    await state.update_data(selected_days=selected_days)
    await callback.message.edit_reply_markup(reply_markup=get_days_keyboard(selected_days))
    await callback.answer()


@router.callback_query(OnboardingStates.preferred_days, F.data == "days_done")
async def process_days_done(callback: CallbackQuery, state: FSMContext):
    """Завершение выбора дней"""
    data = await state.get_data()
    selected_days = data.get("selected_days", [])

    if not selected_days:
        await callback.answer("❌ Выберите хотя бы один день!", show_alert=True)
        return

    await state.update_data(preferred_days=selected_days)

    # Сохранение пользователя
    async with get_session() as db:
        user_data = await state.get_data()

        # Проверяем, существует ли пользователь
        user = await get_user_by_telegram_id(db, callback.from_user.id)

        if user:
            # Обновляем существующего пользователя
            await update_user(
                db,
                callback.from_user.id,
                full_name=user_data["full_name"],
                skills=user_data["skills"],
                experience_shifts=user_data["experience_shifts"],
                course=user_data["course"],
                phone=user_data["phone"],
                preferred_days=user_data["preferred_days"],
                is_registered=True
            )
        else:
            # Создаем нового пользователя
            user = await create_user(
                db,
                callback.from_user.id,
                full_name=user_data["full_name"],
                skills=user_data["skills"],
                experience_shifts=user_data["experience_shifts"],
                course=user_data["course"],
                phone=user_data["phone"],
                preferred_days=user_data["preferred_days"],
                is_registered=True,
                rating=3  # Начальный рейтинг
            )

    await state.clear()

    # Добавление в группы
    await add_user_to_groups(callback.bot, callback.from_user.id)

    await callback.message.edit_text(
        "✅ Регистрация завершена успешно!\n\n"
        f"Ваши данные:\n"
        f"ФИО: {user_data['full_name']}\n"
        f"Курс: {user_data['course']}\n"
        f"Опыт: {user_data['experience_shifts']} смен\n"
        f"Дни работы: {', '.join(selected_days)}\n\n"
        "Выберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "view_shifts")
async def view_shifts(callback: CallbackQuery):
    """Просмотр доступных смен"""
    async with get_session() as db:
        shifts = await get_active_shifts(db, from_date=datetime.utcnow())

        if not shifts:
            await callback.message.edit_text(
                "📋 На данный момент нет доступных смен.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
                ])
            )
            return

        keyboard = []
        for shift in shifts:
            date_str = shift.date.strftime("%d.%m.%Y %H:%M")
            keyboard.append([
                InlineKeyboardButton(
                    text=f"📅 {date_str}",
                    callback_data=f"shift_info_{shift.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])

        await callback.message.edit_text(
            "📋 Доступные смены:\n\nВыберите смену для записи:",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("shift_info_"))
async def shift_info(callback: CallbackQuery):
    """Информация о смене"""
    shift_id = int(callback.data.replace("shift_info_", ""))

    async with get_session() as db:
        from database.crud import get_shift_by_id
        shift = await get_shift_by_id(db, shift_id)

        if not shift:
            await callback.answer("❌ Смена не найдена!", show_alert=True)
            return

        date_str = shift.date.strftime("%d.%m.%Y %H:%M")
        description = shift.description or "Описание отсутствует"

        keyboard = [
            [InlineKeyboardButton(text="✅ Записаться на смену", callback_data=f"book_shift_{shift_id}")],
            [InlineKeyboardButton(text="◀️ Назад к сменам", callback_data="view_shifts")]
        ]

        await callback.message.edit_text(
            f"📅 Смена\n\n"
            f"Дата и время: {date_str}\n"
            f"Описание: {description}",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("book_shift_"))
async def book_shift(callback: CallbackQuery):
    """Запись на смену"""
    shift_id = int(callback.data.replace("book_shift_", ""))

    async with get_session() as db:
        assignment = await assign_user_to_shift(db, callback.from_user.id, shift_id)

        if assignment is None:
            await callback.answer("❌ Не удалось записаться. Возможно, вы уже записаны на эту смену.", show_alert=True)
            return

        await callback.answer("✅ Вы успешно записались на смену!", show_alert=True)
        await callback.message.edit_text(
            "✅ Вы успешно записались на смену!\n\nВыберите действие:",
            reply_markup=get_main_menu_keyboard()
        )


@router.callback_query(F.data == "my_shifts")
async def my_shifts(callback: CallbackQuery):
    """Просмотр своих записей"""
    async with get_session() as db:
        shifts = await get_user_shifts(db, callback.from_user.id, only_future=True)

        if not shifts:
            await callback.message.edit_text(
                "📝 У вас нет записей на предстоящие смены.",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")]
                ])
            )
            return

        text = "📝 Ваши записи на смены:\n\n"
        keyboard = []

        for shift in shifts:
            date_str = shift.date.strftime("%d.%m.%Y %H:%M")
            text += f"📅 {date_str}\n"
            if shift.description:
                text += f"   {shift.description}\n"
            text += "\n"
            keyboard.append([
                InlineKeyboardButton(
                    text=f"❌ Отменить {date_str}",
                    callback_data=f"cancel_shift_{shift.id}"
                )
            ])

        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="main_menu")])

        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )


@router.callback_query(F.data.startswith("cancel_shift_"))
async def cancel_shift(callback: CallbackQuery):
    """Отмена записи на смену"""
    shift_id = int(callback.data.replace("cancel_shift_", ""))

    async with get_session() as db:
        success = await cancel_shift_assignment(db, callback.from_user.id, shift_id)

        if success:
            await callback.answer("✅ Запись на смену отменена!", show_alert=True)
            await my_shifts(callback)  # Обновляем список
        else:
            await callback.answer("❌ Не удалось отменить запись!", show_alert=True)


@router.callback_query(F.data == "update_availability")
async def update_availability_start(callback: CallbackQuery, state: FSMContext):
    """Начало обновления доступности"""
    await callback.message.edit_text(
        "📅 Выберите предпочитаемые дни для работы на следующую неделю:\n"
        "(Нажмите на дни, чтобы выбрать/снять выбор, затем нажмите 'Готово')",
        reply_markup=get_days_keyboard()
    )
    await state.set_state(UpdateAvailabilityStates.preferred_days)
    await state.update_data(selected_days=[])


@router.callback_query(UpdateAvailabilityStates.preferred_days, F.data.startswith("day_"))
async def update_availability_day_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня при обновлении доступности"""
    day = callback.data.replace("day_", "")
    data = await state.get_data()
    selected_days = data.get("selected_days", [])

    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.append(day)

    await state.update_data(selected_days=selected_days)
    await callback.message.edit_reply_markup(reply_markup=get_days_keyboard(selected_days))
    await callback.answer()


@router.callback_query(UpdateAvailabilityStates.preferred_days, F.data == "days_done")
async def update_availability_done(callback: CallbackQuery, state: FSMContext):
    """Завершение обновления доступности"""
    data = await state.get_data()
    selected_days = data.get("selected_days", [])

    if not selected_days:
        await callback.answer("❌ Выберите хотя бы один день!", show_alert=True)
        return

    async with get_session() as db:
        await update_user(db, callback.from_user.id, preferred_days=selected_days)

    await state.clear()

    await callback.message.edit_text(
        f"✅ Ваша доступность обновлена!\n\nВыбранные дни: {', '.join(selected_days)}\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data.startswith("update_day_"))
async def weekly_update_day_selection(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора дня из еженедельного обновления"""
    day = callback.data.replace("update_day_", "")

    # Устанавливаем состояние, если его еще нет
    current_state = await state.get_state()
    if current_state != UpdateAvailabilityStates.preferred_days:
        await state.set_state(UpdateAvailabilityStates.preferred_days)
        await state.update_data(selected_days=[])

    data = await state.get_data()
    selected_days = data.get("selected_days", [])

    if day in selected_days:
        selected_days.remove(day)
    else:
        selected_days.append(day)

    await state.update_data(selected_days=selected_days)

    # Обновляем клавиатуру
    from scheduler.weekly_update import get_days_keyboard_for_update
    await callback.message.edit_reply_markup(reply_markup=get_days_keyboard_for_update(selected_days))
    await callback.answer()


@router.callback_query(F.data == "update_days_done")
async def weekly_update_days_done(callback: CallbackQuery, state: FSMContext):
    """Завершение еженедельного обновления доступности"""
    data = await state.get_data()
    selected_days = data.get("selected_days", [])

    if not selected_days:
        await callback.answer("❌ Выберите хотя бы один день!", show_alert=True)
        return

    async with get_session() as db:
        await update_user(db, callback.from_user.id, preferred_days=selected_days)

    await state.clear()

    await callback.message.edit_text(
        f"✅ Ваша доступность обновлена!\n\nВыбранные дни: {', '.join(selected_days)}\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )


@router.callback_query(F.data == "main_menu")
async def main_menu(callback: CallbackQuery):
    """Возврат в главное меню"""
    await callback.message.edit_text(
        "👋 Главное меню\n\nВыберите действие:",
        reply_markup=get_main_menu_keyboard()
    )

