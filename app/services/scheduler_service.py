import asyncio
from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.dialog_service import voca_service
from app.core.logging import LoggerMixin


class SchedulerService(LoggerMixin):
    """Сервис для планирования периодических задач"""
    
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
        self._db_session_factory = None
    
    def set_db_session_factory(self, session_factory):
        """Устанавливает фабрику сессий базы данных"""
        self._db_session_factory = session_factory
    
    async def start_hourly_download(self):
        """Запускает периодическую загрузку записей каждый час"""
        if self._running:
            self.logger.warning("Планировщик уже запущен")
            return
        
        self._running = True
        self.logger.info("Запуск планировщика почасовой загрузки записей")
        
        try:
            while self._running:
                # Вычисляем время до следующего часа
                now = datetime.now()
                next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
                wait_seconds = (next_hour - now).total_seconds()
                
                self.logger.info(f"Следующая загрузка записей в {next_hour.strftime('%Y-%m-%d %H:%M:%S')}")
                
                # Ждем до следующего часа
                await asyncio.sleep(wait_seconds)
                
                if not self._running:
                    break
                
                # Запускаем загрузку записей за предыдущий час
                try:
                    self.logger.info("Запуск почасовой загрузки записей")
                    
                    # Создаем сессию базы данных для загрузки
                    if self._db_session_factory:
                        async for db in self._db_session_factory():
                            await voca_service.download_records(db=db)
                            break
                    else:
                        # Если фабрика не установлена, загружаем без сохранения в БД
                        await voca_service.download_records()
                    
                    self.logger.info("Почасовая загрузка записей завершена")
                except Exception as e:
                    self.logger.error(f"Ошибка при почасовой загрузке записей: {e}")
                
        except asyncio.CancelledError:
            self.logger.info("Планировщик остановлен")
        except Exception as e:
            self.logger.error(f"Ошибка в планировщике: {e}")
        finally:
            self._running = False
    
    def start(self):
        """Запускает планировщик в фоновом режиме"""
        if self._task is None or self._task.done():
            self._task = asyncio.create_task(self.start_hourly_download())
            self.logger.info("Планировщик запущен в фоновом режиме")
    
    def stop(self):
        """Останавливает планировщик"""
        self._running = False
        if self._task and not self._task.done():
            self._task.cancel()
            self.logger.info("Планировщик остановлен")
    
    @property
    def is_running(self) -> bool:
        """Проверяет, запущен ли планировщик"""
        return self._running and self._task and not self._task.done()


# Создаем глобальный экземпляр планировщика
scheduler_service = SchedulerService() 