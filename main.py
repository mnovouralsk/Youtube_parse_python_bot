# main.py
import asyncio
import sys
import signal
from bot.bot_main import dp, bot
from core.logger import logger
from config import Config
from core.yt_parser.youtube_checker import YouTubeChecker

# Параметры из конфигурации
config = Config()
CHECK_INTERVAL_HOURS = config.check_interval_hours


class ReleaseTrackerApp:
    """
    Главный управляющий класс приложения Release Tracker.
    Запускает Telegram-бота и периодический парсер YouTube.
    Обеспечивает устойчивость и корректное завершение.
    """

    def __init__(self):
        self.bot = bot
        self.dp = dp
        self._stopping = False
        self._periodic_task = None  # фоновая проверка каналов
        self.checker = YouTubeChecker()

    async def start(self):
        """Запуск бота и фонового парсера"""
        logger.info("🚀 Запуск Release Tracker...")

        # Запуск фоновой проверки каналов
        if not self._periodic_task:
            logger.info("🔎 Запуск фоновой проверки каналов...")
            self._periodic_task = asyncio.create_task(
                self.checker.start_periodic_check()
            )

        # Запуск Telegram-бота
        await self.run_bot()

    async def run_bot(self):
        """Запуск Telegram-бота с авто-перезапуском"""
        while not self._stopping:
            try:
                logger.info("🤖 Запуск Telegram-бота...")
                await self.dp.start_polling(
                    self.bot,
                    skip_updates=True,
                    polling_timeout=10,
                    allowed_updates=self.dp.resolve_used_update_types(),
                )
            except Exception as e:
                logger.error(f"Ошибка в Telegram-боте: {e}", exc_info=True)
                logger.info("Перезапуск бота через 5 секунд...")
                await asyncio.sleep(5)

    async def stop(self, *_):
        """Корректное завершение работы приложения"""
        self._stopping = True
        logger.info("🛑 Остановка Release Tracker...")

        await self.dp.stop()

        # Отмена фонового таска
        if self._periodic_task:
            self._periodic_task.cancel()
            try:
                await self._periodic_task
            except asyncio.CancelledError:
                logger.info("Фоновая проверка каналов остановлена.")

        # Закрытие сессий и хранилищ бота
        await self.bot.session.close()
        await self.dp.storage.close()
        logger.info("✅ Завершение работы.")
        sys.exit(0)


async def main():
    """Точка входа"""
    app = ReleaseTrackerApp()

    # Обработка сигналов остановки (только Unix)
    loop = asyncio.get_running_loop()
    if sys.platform != "win32":
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(app.stop(s)))

    await app.start()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Бот остановлен вручную.")
