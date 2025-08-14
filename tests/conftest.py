import pytest
import asyncio
from typing import AsyncGenerator
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from app.main import app
from app.db.session import get_db
from app.db.base_class import Base
from app.core.config import settings


# Тестовая база данных
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Создание тестового движка
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    echo=False,
)

# Создание тестовой фабрики сессий
TestingSessionLocal = async_sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    """Override для получения тестовой сессии БД"""
    async with TestingSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


@pytest.fixture(scope="session")
def event_loop():
    """Создание event loop для тестов"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(autouse=True)
async def setup_database():
    """Настройка тестовой базы данных"""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield
    
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Получение тестовой сессии БД"""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
def client() -> TestClient:
    """Создание тестового клиента"""
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app) 