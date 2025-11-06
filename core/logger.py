import logging
import os
from config import Config


class Logger:
    """
    Класс-обертка для логирования в проекте Release Tracker.
    Поддерживает единое форматирование, вывод в файл и консоль.
    """

    # Параметры из конфигурации
    config = Config()
    LOG_FILE = config.log_file
    LOG_LEVEL = config.log_level.upper()

    _instance = None  # Singleton

    def __new__(cls):
        """Реализация Singleton — создается только один экземпляр"""
        if cls._instance is None:
            cls._instance = super(Logger, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True

        # Проверяем, что папка для логов существует
        log_dir = os.path.dirname(self.LOG_FILE)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)

        # Создаем форматтер
        formatter = logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )

        # Настройка обработчиков
        file_handler = logging.FileHandler(self.LOG_FILE, encoding="utf-8")
        file_handler.setFormatter(formatter)

        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)

        # Настройка корневого логгера
        self.logger = logging.getLogger("ReleaseTracker")
        self.logger.setLevel(getattr(logging, self.LOG_LEVEL, logging.INFO))
        self.logger.addHandler(file_handler)
        self.logger.addHandler(stream_handler)
        self.logger.propagate = False  # не дублировать логи

        self.logger.info("Логгер инициализирован ✅")

    def get_logger(self, name: str = None) -> logging.Logger:
        """
        Возвращает именованный логгер для конкретного модуля.
        """
        return self.logger if not name else self.logger.getChild(name)

    def set_level(self, level: str):
        """
        Позволяет динамически менять уровень логирования.
        """
        self.logger.setLevel(getattr(logging, level.upper(), logging.INFO))
        self.logger.info(f"Уровень логирования изменен на {level.upper()}")


# Экземпляр Singleton
logger = Logger().get_logger("core")
