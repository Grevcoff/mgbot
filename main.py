import asyncio
import logging
import sys
import os
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

# Загрузка переменных окружения
load_dotenv()

from database import Database
from utils.scheduler import NotificationScheduler, handle_stage_callback
from config import BOT_TOKEN, ADMIN_ID, LOG_LEVEL, LOG_FILE

# Импорт хендлеров
from handlers import start, templates, batches, sell, admin

# Настройка логирования
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL.upper()),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

async def main():
    """Главная функция запуска бота"""
    # Проверка токена
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        logger.error("BOT_TOKEN не установлен! Укажите токен в config.py или переменной окружения.")
        return
    
    # Инициализация бота с улучшенными настройками для работы с сетью
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(
            parse_mode=ParseMode.MARKDOWN
        )
    )
    
    # Инициализация диспетчера
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)
    
    # Инициализация базы данных
    db = Database()
    await db.init()
    logger.info("База данных инициализирована")
    
    # Инициализация планировщика
    scheduler = NotificationScheduler(db, bot)
    
    # Создаём глобальную переменную для доступа к базе данных
    import handlers.start
    import handlers.templates
    import handlers.batches
    import handlers.sell
    
    handlers.start.db = db
    handlers.templates.db = db
    handlers.batches.db = db
    handlers.sell.db = db
    handlers.admin.db = db
    
    # Регистрация хендлеров
    dp.include_router(start.router)
    dp.include_router(templates.router)
    dp.include_router(batches.router)
    dp.include_router(sell.router)
    dp.include_router(admin.router)
    
    # Регистрация обработчиков для callback'ов от уведомлений
    @dp.callback_query(lambda c: c.data.startswith("stage_"))
    async def stage_notification_handler(callback: types.CallbackQuery):
        await handle_stage_callback(callback, db, bot)
    
        
    # Обработка ошибок
    @dp.error()
    async def error_handler(event: types.ErrorEvent):
        logger.error(f"Error in handler {event.exception}")
        
        # Игнорируем сетевые ошибки и ошибки парсинга
        if "ClientConnectorError" in str(event.exception) or "ServerDisconnectedError" in str(event.exception):
            logger.warning("Network error detected, will auto-reconnect")
            return
        
        # Отправка сообщения об ошибке админу (только для критических ошибок)
        try:
            await bot.send_message(
                chat_id=ADMIN_ID,
                text=f"⚠️ Произошла ошибка в боте:\n{str(event.exception)}",
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Failed to send error message to admin: {e}")
    
    # Запуск планировщика
    await scheduler.start()
    logger.info("Планировщик уведомлений запущен")
    
    # Запуск бота с улучшенной обработкой ошибок
    logger.info("Запуск бота...")
    try:
        await dp.start_polling(bot)
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
    finally:
        # Очистка при остановке
        await scheduler.stop()
        if 'bot' in locals():
            await bot.session.close()
        logger.info("Бот остановлен")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    except Exception as e:
        logger.error(f"Критическая ошибка: {e}")
        sys.exit(1)
