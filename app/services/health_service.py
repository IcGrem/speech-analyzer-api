from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from app.schemas.health import HealthResponse
from app.core.config import settings
from app.crud.analysis import analysis_crud


async def check_health(db: AsyncSession) -> HealthResponse:
    """Проверка здоровья приложения"""
    # Проверка подключения к базе данных
    try:
        await db.execute(text("SELECT 1"))
        database_status = "healthy"
        
        # Дополнительная проверка через CRUD - подсчет анализов
        total_analyses = await analysis_crud.count(db)
        
    except Exception:
        database_status = "unhealthy"
    
    return HealthResponse(
        status="healthy" if database_status == "healthy" else "unhealthy",
        timestamp=datetime.now(timezone.utc),
        database=database_status,
        version=settings.VERSION
    ) 