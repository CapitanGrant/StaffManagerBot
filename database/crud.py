from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from datetime import datetime
from typing import List, Optional
from database.models import User, Shift, ShiftAssignment, Settings


# ==================== USER CRUD ====================

async def create_user(db: AsyncSession, telegram_id: int, **kwargs) -> User:
    """Создание нового пользователя"""
    user = User(telegram_id=telegram_id, **kwargs)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def get_user_by_telegram_id(db: AsyncSession, telegram_id: int) -> Optional[User]:
    """Получение пользователя по Telegram ID"""
    result = await db.execute(select(User).where(User.telegram_id == telegram_id))
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, telegram_id: int, **kwargs) -> Optional[User]:
    """Обновление данных пользователя"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if user:
        for key, value in kwargs.items():
            setattr(user, key, value)
        user.updated_at = datetime.utcnow()
        await db.commit()
        await db.refresh(user)
    return user


async def get_all_users(db: AsyncSession, is_registered: Optional[bool] = None) -> List[User]:
    """Получение всех пользователей"""
    query = select(User)
    if is_registered is not None:
        query = query.where(User.is_registered == is_registered)
    result = await db.execute(query)
    return list(result.scalars().all())


async def update_user_rating(db: AsyncSession, telegram_id: int, rating: int) -> Optional[User]:
    """Обновление рейтинга пользователя"""
    if not 1 <= rating <= 5:
        raise ValueError("Рейтинг должен быть от 1 до 5")
    return await update_user(db, telegram_id, rating=rating)


# ==================== SHIFT CRUD ====================

async def create_shift(db: AsyncSession, date: datetime, description: Optional[str] = None) -> Shift:
    """Создание новой смены"""
    shift = Shift(date=date, description=description)
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


async def get_shift_by_id(db: AsyncSession, shift_id: int) -> Optional[Shift]:
    """Получение смены по ID"""
    result = await db.execute(
        select(Shift)
        .where(Shift.id == shift_id)
        .options(selectinload(Shift.assignments).selectinload(ShiftAssignment.user))
    )
    return result.scalar_one_or_none()


async def get_active_shifts(db: AsyncSession, from_date: Optional[datetime] = None) -> List[Shift]:
    """Получение активных смен"""
    query = select(Shift).where(Shift.is_active == True)
    if from_date:
        query = query.where(Shift.date >= from_date)
    query = query.order_by(Shift.date)
    result = await db.execute(query.options(selectinload(Shift.assignments)))
    return list(result.scalars().all())


async def update_shift(db: AsyncSession, shift_id: int, **kwargs) -> Optional[Shift]:
    """Обновление смены"""
    shift = await get_shift_by_id(db, shift_id)
    if shift:
        for key, value in kwargs.items():
            setattr(shift, key, value)
        await db.commit()
        await db.refresh(shift)
    return shift


async def archive_shift(db: AsyncSession, shift_id: int) -> Optional[Shift]:
    """Архивирование смены"""
    return await update_shift(db, shift_id, is_active=False)


# ==================== SHIFT ASSIGNMENT CRUD ====================

async def assign_user_to_shift(db: AsyncSession, telegram_id: int, shift_id: int) -> Optional[ShiftAssignment]:
    """Запись пользователя на смену"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return None
    
    # Проверка, не записан ли уже
    existing = await db.execute(
        select(ShiftAssignment).where(
            ShiftAssignment.user_id == user.id,
            ShiftAssignment.shift_id == shift_id,
            ShiftAssignment.is_cancelled == False
        )
    )
    if existing.scalar_one_or_none():
        return None  # Уже записан
    
    assignment = ShiftAssignment(user_id=user.id, shift_id=shift_id)
    db.add(assignment)
    await db.commit()
    await db.refresh(assignment)
    await db.refresh(user)
    return assignment


async def cancel_shift_assignment(db: AsyncSession, telegram_id: int, shift_id: int) -> bool:
    """Отмена записи на смену"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return False
    
    result = await db.execute(
        select(ShiftAssignment).where(
            ShiftAssignment.user_id == user.id,
            ShiftAssignment.shift_id == shift_id,
            ShiftAssignment.is_cancelled == False
        )
    )
    assignment = result.scalar_one_or_none()
    if assignment:
        assignment.is_cancelled = True
        assignment.cancelled_at = datetime.utcnow()
        await db.commit()
        return True
    return False


async def get_user_shifts(db: AsyncSession, telegram_id: int, only_future: bool = True) -> List[Shift]:
    """Получение смен пользователя"""
    user = await get_user_by_telegram_id(db, telegram_id)
    if not user:
        return []
    
    # Используем подзапрос для получения ID смен, на которые записан пользователь
    from sqlalchemy import distinct
    
    assignment_query = (
        select(ShiftAssignment.shift_id)
        .where(
            ShiftAssignment.user_id == user.id,
            ShiftAssignment.is_cancelled == False
        )
    )
    
    # Основной запрос для получения смен
    query = select(Shift).where(Shift.id.in_(assignment_query))
    
    if only_future:
        query = query.where(Shift.date >= datetime.utcnow())
    
    query = query.where(Shift.is_active == True).order_by(Shift.date)
    result = await db.execute(query)
    return list(result.scalars().all())


# ==================== SETTINGS CRUD ====================

async def get_setting(db: AsyncSession, key: str) -> Optional[str]:
    """Получение настройки"""
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()
    return setting.value if setting else None


async def set_setting(db: AsyncSession, key: str, value: str) -> Settings:
    """Установка настройки"""
    result = await db.execute(select(Settings).where(Settings.key == key))
    setting = result.scalar_one_or_none()
    
    if setting:
        setting.value = value
        setting.updated_at = datetime.utcnow()
    else:
        setting = Settings(key=key, value=value)
        db.add(setting)
    
    await db.commit()
    await db.refresh(setting)
    return setting


async def get_all_registered_users_for_broadcast(db: AsyncSession) -> List[User]:
    """Получение всех зарегистрированных пользователей для рассылки"""
    return await get_all_users(db, is_registered=True)

