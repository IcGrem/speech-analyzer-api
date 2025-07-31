from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import get_db
from app.api.v1.router import api_router
from app.core.logging import setup_logging
from app.services.main_services import ensure_admin_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управление жизненным циклом приложения"""
    # Startup
    setup_logging()
    
    # Создание администратора по умолчанию при запуске
    try:
        async for db in get_db():
            await ensure_admin_exists(db)
            break
    except Exception as e:
        print(f"Ошибка при создании администратора: {e}")
    
    yield
    # Shutdown
    # Здесь можно добавить cleanup логику


def create_application() -> FastAPI:
    """Создание экземпляра FastAPI приложения"""
    app = FastAPI(
        title=settings.PROJECT_NAME,
        version=settings.VERSION,
        description="API для анализа речи",
        lifespan=lifespan,
    )

    # CORS middleware
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
