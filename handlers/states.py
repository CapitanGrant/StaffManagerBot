from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    """Состояния для онбординга"""
    full_name = State()
    skills = State()
    experience_shifts = State()
    course = State()
    phone = State()
    preferred_days = State()


class UpdateAvailabilityStates(StatesGroup):
    """Состояния для обновления доступности"""
    preferred_days = State()


class AdminStates(StatesGroup):
    """Состояния для администратора"""
    waiting_shift_date = State()
    waiting_shift_description = State()
    waiting_shift_edit_id = State()
    waiting_user_telegram_id = State()
    waiting_rating = State()
    waiting_broadcast_message = State()
    waiting_setting_value = State()
    waiting_completed_info = State()

