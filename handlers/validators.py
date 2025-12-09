import re
from typing import Optional


def validate_phone(phone: str) -> bool:
    """Базовая валидация телефона"""
    # Удаляем все символы кроме цифр и +
    cleaned = re.sub(r'[^\d+]', '', phone)
    # Проверяем длину и формат
    return len(cleaned) >= 10 and (cleaned.startswith('+') or cleaned.startswith('8') or cleaned.startswith('7'))


def validate_course(course: str) -> Optional[int]:
    """Валидация курса (1-5)"""
    try:
        course_num = int(course)
        if 1 <= course_num <= 5:
            return course_num
    except ValueError:
        pass
    return None


def validate_experience(experience: str) -> Optional[int]:
    """Валидация опыта (целое число >= 0)"""
    try:
        exp = int(experience)
        if exp >= 0:
            return exp
    except ValueError:
        pass
    return None


def parse_preferred_days(text: str) -> list:
    """Парсинг выбранных дней недели"""
    days_map = {
        'пн': 'Пн', 'понедельник': 'Пн',
        'вт': 'Вт', 'вторник': 'Вт',
        'ср': 'Ср', 'среда': 'Ср',
        'чт': 'Чт', 'четверг': 'Чт',
        'пт': 'Пт', 'пятница': 'Пт',
        'сб': 'Сб', 'суббота': 'Сб',
        'вс': 'Вс', 'воскресенье': 'Вс',
    }
    
    selected_days = []
    text_lower = text.lower()
    
    for key, day in days_map.items():
        if key in text_lower:
            if day not in selected_days:
                selected_days.append(day)
    
    return selected_days if selected_days else None

