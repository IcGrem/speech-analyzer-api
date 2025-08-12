from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, update

from app.crud.base import CRUDBase
from app.models.dialogs import AudioData, AudioDataForAnalysis
from app.schemas.audio_data import AudioDataCreate, AudioDataUpdate, AudioDataForAnalysisCreate, AudioDataForAnalysisUpdate


class CRUDAudioData(CRUDBase[AudioData, AudioDataCreate, AudioDataUpdate]):
    """CRUD операции для модели AudioData"""
    
    async def get_by_audio_data_id(self, db: AsyncSession, audio_data_id: int) -> Optional[AudioData]:
        """Получить запись по audio_data_id"""
        query = select(self.model).where(self.model.audio_data_id == audio_data_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_id(self, db: AsyncSession, id: Any) -> Optional[AudioData]:
        """Получить запись по ID (первичный ключ)"""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_filename(self, db: AsyncSession, filename: str) -> Optional[AudioData]:
        """Получить запись по имени файла"""
        query = select(self.model).where(self.model.filename == filename)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_unprocessed(self, db: AsyncSession, limit: int = 100) -> List[AudioData]:
        """Получить необработанные записи"""
        return await self.get_multi(db, is_processed=False, limit=limit, order_by="creation_date")
    
    async def get_by_employee_id(self, db: AsyncSession, employee_id: int) -> List[AudioData]:
        """Получить записи по ID сотрудника"""
        return await self.get_multi(db, employee_id=employee_id, order_by="-creation_date")
    
    async def get_by_date_range(
        self, 
        db: AsyncSession, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[AudioData]:
        """Получить записи в диапазоне дат"""
        return await self.get_multi(
            db,
            creation_date__gte=start_date,
            creation_date__lte=end_date,
            order_by="-creation_date"
        )
    
    async def get_unprocessed_by_employee_and_date(
        self, 
        db: AsyncSession, 
        employee_id: int, 
        date: datetime
    ) -> List[AudioData]:
        """Получить необработанные записи для сотрудника за определенную дату"""
        # Нормализуем дату до дня
        date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = date_only + timedelta(days=1)
        
        query = select(self.model).where(
            and_(
                self.model.employee_id == employee_id,
                self.model.creation_date >= date_only,
                self.model.creation_date < next_day,
                self.model.is_processed == False
            )
        ).order_by(self.model.creation_date)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_unprocessed_by_previous_day(
        self, 
        db: AsyncSession, 
        target_date: datetime
    ) -> List[AudioData]:
        """Получить необработанные записи за предыдущие сутки от указанной даты"""
        # Нормализуем целевую дату до дня
        target_date_only = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        previous_day_start = target_date_only - timedelta(days=1)
        previous_day_end = target_date_only
        
        query = select(self.model).where(
            and_(
                self.model.creation_date >= previous_day_start,
                self.model.creation_date < previous_day_end,
                self.model.is_processed == False
            )
        ).order_by(self.model.employee_id, self.model.creation_date)
        
        result = await db.execute(query)
        return result.scalars().all()
    
    async def mark_multiple_as_processed(
        self, 
        db: AsyncSession, 
        audio_data_ids: List[int]
    ) -> int:
        """Отметить несколько записей как обработанные"""
        if not audio_data_ids:
            return 0
        
        query = (
            update(self.model)
            .where(self.model.audio_data_id.in_(audio_data_ids))
            .values(is_processed=True)
        )
        
        result = await db.execute(query)
        await db.commit()
        return result.rowcount
    
    async def mark_as_processed(self, db: AsyncSession, audio_data_id: int) -> Optional[AudioData]:
        """Отметить запись как обработанную"""
        return await self.update_by_field(
            db, 
            "audio_data_id", 
            audio_data_id, 
            {"is_processed": True}
        )
    
    async def mark_as_unprocessed(self, db: AsyncSession, audio_data_id: int) -> Optional[AudioData]:
        """Отметить запись как необработанную"""
        return await self.update_by_field(
            db, 
            "audio_data_id", 
            audio_data_id, 
            {"is_processed": False}
        )
    
    async def get_processed_count(self, db: AsyncSession) -> int:
        """Получить количество обработанных записей"""
        return await self.count(db, is_processed=True)
    
    async def get_unprocessed_count(self, db: AsyncSession) -> int:
        """Получить количество необработанных записей"""
        return await self.count(db, is_processed=False)
    
    async def get_total_count(self, db: AsyncSession) -> int:
        """Получить общее количество записей"""
        return await self.count(db)
    
    async def create_from_voca_record(
        self, 
        db: AsyncSession, 
        voca_record: Dict[str, Any], 
        filename: str
    ) -> AudioData:
        """Создать запись AudioData из данных Voca API"""
        
        # Преобразуем даты из строк в datetime
        creation_date = datetime.fromisoformat(voca_record['creationDate'].replace('Z', '+00:00'))
        receive_date = datetime.fromisoformat(voca_record['receiveDate'].replace('Z', '+00:00'))
        end_date = datetime.fromisoformat(voca_record['endDate'].replace('Z', '+00:00'))
        
        audio_data = AudioDataCreate(
            audio_data_id=voca_record['id'],
            creation_date=creation_date,
            receive_date=receive_date,
            end_date=end_date,
            duration_sec=voca_record['durationSec'],
            employee_id=voca_record['employeeId'],
            employee_number=voca_record['employeeNumber'],
            employee_name=voca_record['employeeName'],
            employee_position=voca_record['employeePosition'],
            device_id=voca_record['deviceId'],
            device_description=voca_record['deviceDescription'],
            unit_id=voca_record['unitId'],
            unit_name=voca_record['unitName'],
            unit_code=voca_record['unitCode'],
            is_expired=voca_record['isExpired'],
            filename=filename,
            is_processed=False
        )
        
        return await self.create(db, audio_data)


# Создаем экземпляр для использования в сервисах
audio_data_crud = CRUDAudioData(AudioData)


class CRUDAudioDataForAnalysis(CRUDBase[AudioDataForAnalysis, AudioDataForAnalysisCreate, AudioDataForAnalysisUpdate]):
    """CRUD операции для модели AudioDataForAnalysis"""
    
    async def get_by_employee_and_date(
        self, 
        db: AsyncSession, 
        employee_id: int, 
        date: datetime
    ) -> Optional[AudioDataForAnalysis]:
        """Получить запись по employee_id и дате"""
        # Нормализуем дату до дня (убираем время)
        date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        query = select(self.model).where(
            and_(
                self.model.employee_id == employee_id,
                func.date(self.model.date) == func.date(date_only)
            )
        )
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def create_or_update_for_employee_date(
        self, 
        db: AsyncSession, 
        employee_id: int, 
        date: datetime, 
        full_audio_filename: str
    ) -> AudioDataForAnalysis:
        """Создать или обновить запись для сотрудника и даты"""
        # Нормализуем дату до дня
        date_only = date.replace(hour=0, minute=0, second=0, microsecond=0)
        
        existing = await self.get_by_employee_and_date(db, employee_id, date_only)
        
        if existing:
            # Обновляем существующую запись
            return await self.update(
                db, 
                existing, 
                AudioDataForAnalysisUpdate(full_audio_filename=full_audio_filename)
            )
        else:
            # Создаем новую запись
            return await self.create(
                db, 
                AudioDataForAnalysisCreate(
                    employee_id=employee_id,
                    date=date_only,
                    full_audio_filename=full_audio_filename
                )
            )


# Создаем экземпляр для использования в сервисах
audio_data_for_analysis_crud = CRUDAudioDataForAnalysis(AudioDataForAnalysis)
