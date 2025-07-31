import logging
import sys
from typing import Any

from app.core.config import settings


def setup_logging() -> None:
    """Настройка логирования"""
    logging.basicConfig(
        level=getattr(logging, settings.LOG_LEVEL),
        format=settings.LOG_FORMAT,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Настройка логгеров для внешних библиотек
    logging.getLogger("uvicorn.access").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """Получение логгера с указанным именем"""
    return logging.getLogger(name)


class LoggerMixin:
    """Mixin для добавления логгера в классы"""
    
    @property
    def logger(self) -> logging.Logger:
        """Логгер для класса"""
        return get_logger(self.__class__.__name__)
    
