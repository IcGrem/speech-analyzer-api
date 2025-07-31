from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.crud.base import CRUDBase
from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisUpdate


class CRUDAnalysis(CRUDBase[Analysis, AnalysisCreate, AnalysisUpdate]):
    """CRUD операции для модели Analysis"""
    
    async def get_by_status(self, db: AsyncSession, status: str) -> List[Analysis]:
        """Получить анализы по статусу"""
        return await self.get_multi(db, status=status)
    
    async def get_pending_analyses(self, db: AsyncSession) -> List[Analysis]:
        """Получить все ожидающие анализы"""
        return await self.get_by_status(db, "pending")
    
    async def get_processing_analyses(self, db: AsyncSession) -> List[Analysis]:
        """Получить все обрабатываемые анализы"""
        return await self.get_by_status(db, "processing")
    
    async def get_completed_analyses(self, db: AsyncSession) -> List[Analysis]:
        """Получить все завершенные анализы"""
        return await self.get_by_status(db, "completed")
    
    async def get_failed_analyses(self, db: AsyncSession) -> List[Analysis]:
        """Получить все неудачные анализы"""
        return await self.get_by_status(db, "failed")
    
    async def update_status(self, db: AsyncSession, analysis_id: UUID, status: str) -> Optional[Analysis]:
        """Обновить статус анализа"""
        return await self.update_by_field(db, "id", analysis_id, {"status": status})
    
    async def update_result(self, db: AsyncSession, analysis_id: UUID, result: dict, status: str = "completed") -> Optional[Analysis]:
        """Обновить результат анализа"""
        update_data = {"result": result, "status": status}
        return await self.update_by_field(db, "id", analysis_id, update_data)


# Создаем экземпляр для использования в сервисах
analysis_crud = CRUDAnalysis(Analysis) 