from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.scheduler_service import scheduler_service
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


class SchedulerStatus(BaseModel):
    """Модель статуса планировщика"""
    is_running: bool
    message: str


@router.get("/scheduler/status", response_model=SchedulerStatus)
async def get_scheduler_status():
    """Получить статус планировщика"""
    try:
        is_running = scheduler_service.is_running
        message = "Планировщик активен" if is_running else "Планировщик остановлен"
        
        return SchedulerStatus(
            is_running=is_running,
            message=message
        )
    except Exception as e:
        logger.error(f"Ошибка при получении статуса планировщика: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при получении статуса планировщика")


@router.post("/scheduler/start", response_model=SchedulerStatus)
async def start_scheduler():
    """Запустить планировщик"""
    try:
        if scheduler_service.is_running:
            return SchedulerStatus(
                is_running=True,
                message="Планировщик уже запущен"
            )
        
        scheduler_service.start()
        logger.info("Планировщик запущен через API")
        
        return SchedulerStatus(
            is_running=True,
            message="Планировщик успешно запущен"
        )
    except Exception as e:
        logger.error(f"Ошибка при запуске планировщика: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при запуске планировщика")


@router.post("/scheduler/stop", response_model=SchedulerStatus)
async def stop_scheduler():
    """Остановить планировщик"""
    try:
        if not scheduler_service.is_running:
            return SchedulerStatus(
                is_running=False,
                message="Планировщик уже остановлен"
            )
        
        scheduler_service.stop()
        logger.info("Планировщик остановлен через API")
        
        return SchedulerStatus(
            is_running=False,
            message="Планировщик успешно остановлен"
        )
    except Exception as e:
        logger.error(f"Ошибка при остановке планировщика: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при остановке планировщика")


@router.post("/scheduler/restart", response_model=SchedulerStatus)
async def restart_scheduler():
    """Перезапустить планировщик"""
    try:
        # Останавливаем если запущен
        if scheduler_service.is_running:
            scheduler_service.stop()
        
        # Запускаем заново
        scheduler_service.start()
        logger.info("Планировщик перезапущен через API")
        
        return SchedulerStatus(
            is_running=True,
            message="Планировщик успешно перезапущен"
        )
    except Exception as e:
        logger.error(f"Ошибка при перезапуске планировщика: {e}")
        raise HTTPException(status_code=500, detail="Ошибка при перезапуске планировщика") 