from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import get_db
from app.api.v1.router import api_router
from app.core.logging import setup_logging, get_logger
from app.services.main_services import ensure_admin_exists
from app.services.scheduler_service import scheduler_service

setup_logging()
logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    # setup_logging()
    # logger = get_logger(__name__)
    
    # Создание администратора по умолчанию при запуске
    try:
        async for db in get_db():
            await ensure_admin_exists(db)
            break
    except Exception as e:
        logger.error(f"Ошибка при создании администратора: {e}")
    
    # Запуск планировщика почасовой загрузки записей
    try:
        if settings.ENABLE_HOURLY_DOWNLOAD:
            # Устанавливаем фабрику сессий базы данных в планировщик
            scheduler_service.set_db_session_factory(get_db)
            scheduler_service.start()
            logger.info("Планировщик почасовой загрузки записей запущен")
        else:
            logger.info("Планировщик почасовой загрузки записей отключен в настройках")
    except Exception as e:
        logger.error(f"Ошибка при запуске планировщика: {e}")
    
    yield
    
    # Shutdown
    # Остановка планировщика
    try:
        scheduler_service.stop()
        logger.info("Планировщик почасовой загрузки записей остановлен")
    except Exception as e:
        logger.error(f"Ошибка при остановке планировщика: {e}")


def create_application() -> FastAPI:
    """Создание экземпляра FastAPI приложения"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="API для анализа речи",
        lifespan=lifespan,
    )

    # CORS middleware
    logger.info(f"ALLOWED_HOSTS: {settings.ALLOWED_HOSTS}")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_HOSTS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Подключение роутеров
    app.include_router(api_router, prefix="/api/v1")

    return app


app = create_application()
