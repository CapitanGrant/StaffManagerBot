from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from config import Config

# Создание движка базы данных
engine = create_async_engine(Config.DATABASE_URL, echo=False, future=True)

# Создание сессии
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Инициализация базы данных (создание таблиц и обновление схемы)"""
    from database.models import Base
    from sqlalchemy import text

    async with engine.begin() as conn:
        # Создаем все таблицы
        await conn.run_sync(Base.metadata.create_all)
        
        # Пытаемся добавить поле completed_info, если его нет (для существующих БД)
        # Игнорируем ошибку, если поле уже существует
        try:
            await conn.execute(text('ALTER TABLE shifts ADD COLUMN completed_info TEXT'))
            print("✅ Поле completed_info добавлено в таблицу shifts")
        except Exception as e:
            # Ошибка ожидаема, если поле уже существует или таблицы нет
            error_msg = str(e).lower()
            if 'duplicate column' in error_msg or 'already exists' in error_msg or 'no such table' in error_msg:
                pass  # Поле уже существует или таблица не создана (будет создана выше)
            else:
                print(f"⚠️ Предупреждение при обновлении схемы БД: {e}")

@asynccontextmanager
async def get_session() -> AsyncSession:
    """Получение сессии базы данных (для прямого использования)"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
