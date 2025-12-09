import os
from dotenv import load_dotenv
from typing import List

load_dotenv()

class Config:
    """Конфигурация бота"""
    
    # Токен бота
    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    
    # URL базы данных
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
        return user_id in Config.ADMIN_CHAT_IDS

