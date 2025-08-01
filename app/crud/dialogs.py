from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import joinedload

from app.crud.base import CRUDBase
from app.models.dialogs import Dialog, ConversationType
from app.schemas.dialogs import DialogCreate, DialogUpdate


class CRUDDialog(CRUDBase[Dialog, DialogCreate, DialogUpdate]):
    """CRUD операции для модели Dialog"""
    
    async def get_all(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги"""
        return await self.get_multi(db)
    
    async def get_by_employee(self, db: AsyncSession, employee_id: UUID) -> List[Dialog]:
        """Получить все диалоги сотрудника"""
        return await self.get_multi(db, employee_id=employee_id)
    
    async def get_by_conversation_type(self, db: AsyncSession, conversation_type: ConversationType) -> List[Dialog]:
        """Получить диалоги по типу разговора"""
        return await self.get_multi(db, conversation_type=conversation_type)
    
    async def get_m2m_dialogs(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги manager-to-manager"""
        return await self.get_by_conversation_type(db, ConversationType.M2M)
    
    async def get_m2c_dialogs(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги manager-to-customer"""
        return await self.get_by_conversation_type(db, ConversationType.M2C)
    
    async def get_unknown_dialogs(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги с неизвестным типом"""
        return await self.get_by_conversation_type(db, ConversationType.UNKNOWN)
    
    async def get_by_filename(self, db: AsyncSession, filename: str) -> Optional[Dialog]:
        """Получить диалог по имени файла"""
        return await self.get_by_field(db, "filename", filename)
    
    async def get_by_date_range(
        self, 
        db: AsyncSession, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dialog]:
        """Получить диалоги в диапазоне дат записи"""
        return await self.get_multi(
            db,
            recording_start_date__gte=start_date,
            recording_end_date__lte=end_date
        )
    
    async def get_by_recording_date(self, db: AsyncSession, date: datetime) -> List[Dialog]:
        """Получить диалоги по дате записи"""
        return await self.get_multi(
            db,
            recording_start_date__date=date.date()
        )
    
    async def search_by_filename(self, db: AsyncSession, filename_part: str) -> List[Dialog]:
        """Поиск диалогов по части имени файла"""
        return await self.get_multi(db, filename__icontains=filename_part)
    
    async def get_employee_dialogs_by_type(
        self, 
        db: AsyncSession, 
        employee_id: UUID, 
        conversation_type: ConversationType
    ) -> List[Dialog]:
        """Получить диалоги сотрудника определенного типа"""
        return await self.get_multi(
            db,
            employee_id=employee_id,
            conversation_type=conversation_type
        )
    
    async def get_recent_dialogs(self, db: AsyncSession, days: int = 7) -> List[Dialog]:
        """Получить диалоги за последние N дней"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        return await self.get_multi(
            db,
            recording_start_date__gte=cutoff_date,
            order_by="-recording_start_date"
        )
    
    async def update_conversation_type(
        self, 
        db: AsyncSession, 
        dialog_id: UUID, 
        conversation_type: ConversationType
    ) -> Optional[Dialog]:
        """Обновить тип разговора"""
        return await self.update_by_field(
            db, 
            "id", 
            dialog_id, 
            {"conversation_type": conversation_type}
        )
    
    async def update_conversation_data(
        self, 
        db: AsyncSession, 
        dialog_id: UUID, 
        conversation_data: dict
    ) -> Optional[Dialog]:
        """Обновить данные разговора"""
        return await self.update_by_field(
            db, 
            "id", 
            dialog_id, 
            {"conversation": conversation_data}
        )
    
    async def get_employee_metrics_by_organization(
        self, 
        db: AsyncSession, 
        organization_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Получить метрики сотрудников организации с фильтром по датам"""
        from app.models.users import Employee
        
        query = select(
            Employee.id,
            Employee.first_name,
            Employee.last_name,
            func.avg(Dialog.greeting_farewell_score).label("avg_greeting_farewell"),
            func.avg(Dialog.completeness_score).label("avg_completeness"),
            func.avg(Dialog.tone_score).label("avg_tone"),
            func.avg(Dialog.openness_helpfulness_score).label("avg_openness_helpfulness"),
            func.avg(Dialog.listening_score).label("avg_listening"),
            func.avg(Dialog.empathy_score).label("avg_empathy"),
            func.avg(Dialog.speech_quality_score).label("avg_speech_quality"),
            func.avg(Dialog.response_time_score).label("avg_response_time"),
            func.avg(Dialog.overall_score).label("avg_overall"),
            func.count(Dialog.id).label("dialog_count")
        ).join(Employee, Dialog.employee_id == Employee.id).where(
            Employee.organization_id == organization_id
        )
        
        if start_date:
            query = query.where(Dialog.recording_start_date >= start_date)
        if end_date:
            query = query.where(Dialog.recording_end_date <= end_date)
            
        query = query.group_by(Employee.id, Employee.first_name, Employee.last_name)
        
        result = await db.execute(query)
        return result.fetchall()
    
    async def get_organization_daily_metrics(
        self, 
        db: AsyncSession, 
        organization_id: int,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Получить суммарные метрики организации по дням"""
        from app.models.users import Employee
        
        query = select(
            func.date(Dialog.recording_start_date).label("date"),
            func.avg(Dialog.greeting_farewell_score).label("avg_greeting_farewell"),
            func.avg(Dialog.completeness_score).label("avg_completeness"),
            func.avg(Dialog.tone_score).label("avg_tone"),
            func.avg(Dialog.openness_helpfulness_score).label("avg_openness_helpfulness"),
            func.avg(Dialog.listening_score).label("avg_listening"),
            func.avg(Dialog.empathy_score).label("avg_empathy"),
            func.avg(Dialog.speech_quality_score).label("avg_speech_quality"),
            func.avg(Dialog.response_time_score).label("avg_response_time"),
            func.avg(Dialog.overall_score).label("avg_overall"),
            func.count(Dialog.id).label("total_dialogs")
        ).join(Employee, Dialog.employee_id == Employee.id).where(
            Employee.organization_id == organization_id
        )
        
        if start_date:
            query = query.where(Dialog.recording_start_date >= start_date)
        if end_date:
            query = query.where(Dialog.recording_end_date <= end_date)
            
        query = query.group_by(func.date(Dialog.recording_start_date))
        query = query.order_by(func.date(Dialog.recording_start_date))
        
        result = await db.execute(query)
        return result.fetchall()


# Создаем экземпляр для использования в сервисах
dialog_crud = CRUDDialog(Dialog) 