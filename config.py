import os
from dotenv import load_dotenv
from typing import List


load_dotenv()

class Config:
    """Конфигурация бота"""
    
    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "").strip()
    
    # URL базы данных
    # Для Docker используйте абсолютный путь в .env: sqlite+aiosqlite:////app/data/staff_bot.db
    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./staff_bot.db")
    
    # ID администраторов (можно несколько через запятую)
    ADMIN_CHAT_IDS: List[int] = [
        int(chat_id.strip()) 
        for chat_id in os.getenv("ADMIN_CHAT_IDS", "").split(",") 
        if chat_id.strip().isdigit()
    ]
    
    # ID рабочего чата
    WORK_GROUP_ID: int = int(os.getenv("WORK_GROUP_ID", "0")) if os.getenv("WORK_GROUP_ID", "0").isdigit() else 0
    
    # ID канала уведомлений
    NOTIFICATION_CHANNEL_ID: int = int(os.getenv("NOTIFICATION_CHANNEL_ID", "0")) if os.getenv("NOTIFICATION_CHANNEL_ID", "0").isdigit() else 0
    
    @staticmethod
    def is_admin(user_id: int) -> bool:
        """Проверка, является ли пользователь администратором"""
        # Проверяем в .env
        if user_id in Config.ADMIN_CHAT_IDS:
            return True
        
        # Проверяем в БД (если доступна)
        try:
            from database.database import get_session
            from database.crud import get_setting
            import asyncio
            
            # Создаем новый event loop если нужно
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Проверяем синхронно (для простоты используем sync подход)
            # В реальных условиях лучше проверять через async функцию
            return False  # Будет проверяться в handlers через get_setting
        except:
            return False

