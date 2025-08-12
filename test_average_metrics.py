import asyncio
import sys
import os
from datetime import datetime
from uuid import UUID

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.crud.dialogs import dialog_crud
from app.db.session import get_db
from app.core.logging import get_logger

async def test_average_metrics():
    logger = get_logger(__name__)
    
    # Тестовый organization_id (замените на реальный)
    organization_id = UUID("550e8400-e29b-41d4-a716-446655440000")  # Замените на реальный ID
    
    async for db in get_db():
        try:
            logger.info(f"Тестируем получение средних метрик для организации {organization_id}")
            
            # Получаем средние метрики без фильтра по датам
            result = await dialog_crud.get_organization_average_metrics(db, organization_id)
            logger.info(f"Результат без фильтра дат: {result}")
            
            # Получаем средние метрики с фильтром по датам
            start_date = datetime(2025, 7, 1)
            end_date = datetime(2025, 8, 1)
            result_with_dates = await dialog_crud.get_organization_average_metrics(
                db, organization_id, start_date, end_date
            )
            logger.info(f"Результат с фильтром дат: {result_with_dates}")
            
        except Exception as e:
            logger.error(f"Ошибка при тестировании: {e}")
        finally:
            break

if __name__ == "__main__":
    asyncio.run(test_average_metrics())
