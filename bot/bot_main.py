from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage

from core.logger import logger
from config import Config
from bot.handlers import router
from bot.moderation import router_moderation


# Загрузка конфигурации
config = Config()

# Создаем бот и диспетчер
bot = Bot(token=config.bot_token)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Регистрация роутеров
dp.include_router(router)
dp.include_router(router_moderation)

logger.info("Бот и диспетчер инициализированы")
