from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    telegram_id = Column(Integer, unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    skills = Column(Text, nullable=True)
    experience_shifts = Column(Integer, default=0, nullable=False)
    course = Column(Integer, nullable=False)  # 1-5
    phone = Column(String(20), nullable=False)
    preferred_days = Column(JSON, nullable=True)  # Список дней недели ["Пн", "Вт", ...]
    rating = Column(Integer, default=3, nullable=False)  # 1-5
    is_registered = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Связи
    shifts = relationship("ShiftAssignment", back_populates="user", cascade="all, delete-orphan")


class Shift(Base):
    """Модель смены"""
    __tablename__ = "shifts"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, nullable=False, index=True)
    description = Column(Text, nullable=True)
    completed_info = Column(Text, nullable=True)  # Информация о выполненной работе на смене
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Связи
    assignments = relationship("ShiftAssignment", back_populates="shift", cascade="all, delete-orphan")


class ShiftAssignment(Base):
    """Модель записи пользователя на смену"""
    __tablename__ = "shift_assignments"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    shift_id = Column(Integer, ForeignKey("shifts.id"), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    is_cancelled = Column(Boolean, default=False, nullable=False)
    cancelled_at = Column(DateTime, nullable=True)
    
    # Связи
    user = relationship("User", back_populates="shifts")
    shift = relationship("Shift", back_populates="assignments")


class Settings(Base):
    """Модель настроек системы"""
    __tablename__ = "settings"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

