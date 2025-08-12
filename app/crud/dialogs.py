from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.dialogs import Dialog, ConversationType
from app.schemas.dialogs import DialogCreate, DialogUpdate


class CRUDDialog(CRUDBase[Dialog, DialogCreate, DialogUpdate]):
    """CRUD операции для модели Dialog"""
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[Dialog]:
        """Получить диалог по ID с загрузкой сотрудника"""
        query = select(self.model).options(selectinload(self.model.employee)).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги с загрузкой сотрудников"""
        return await self.get_multi(db)
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = None,
        **filters
    ) -> List[Dialog]:
        """Получить список диалогов с фильтрацией, пагинацией и загрузкой сотрудников"""
        query = select(self.model).options(selectinload(self.model.employee))
        
        # Применяем фильтры
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                if field.endswith('__icontains'):
                    # Поддержка поиска по подстроке
                    actual_field = field.replace('__icontains', '')
                    if hasattr(self.model, actual_field):
                        query = query.where(getattr(self.model, actual_field).ilike(f'%{value}%'))
                elif field.endswith('__gte'):
                    # Поддержка фильтра >=
                    actual_field = field.replace('__gte', '')
                    if hasattr(self.model, actual_field):
                        query = query.where(getattr(self.model, actual_field) >= value)
                elif field.endswith('__lte'):
                    # Поддержка фильтра <=
                    actual_field = field.replace('__lte', '')
                    if hasattr(self.model, actual_field):
                        query = query.where(getattr(self.model, actual_field) <= value)
                elif field.endswith('__date'):
                    # Поддержка фильтра по дате
                    actual_field = field.replace('__date', '')
                    if hasattr(self.model, actual_field):
                        query = query.where(func.date(getattr(self.model, actual_field)) == value)
                else:
                    query = query.where(getattr(self.model, field) == value)
        
        # Применяем сортировку
        if order_by:
            if order_by.startswith('-'):
                field_name = order_by[1:]
                if hasattr(self.model, field_name):
                    query = query.order_by(getattr(self.model, field_name).desc())
            else:
                if hasattr(self.model, order_by):
                    query = query.order_by(getattr(self.model, order_by))
        
        query = query.offset(skip).limit(limit)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_by_employee(self, db: AsyncSession, employee_id: UUID) -> List[Dialog]:
        """Получить все диалоги сотрудника с загрузкой сотрудников"""
        return await self.get_multi(db, employee_id=employee_id)
    
    async def get_by_conversation_type(self, db: AsyncSession, conversation_type: ConversationType) -> List[Dialog]:
        """Получить диалоги по типу разговора с загрузкой сотрудников"""
        return await self.get_multi(db, conversation_type=conversation_type)
    
    async def get_m2m_dialogs(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги manager-to-manager с загрузкой сотрудников"""
        return await self.get_by_conversation_type(db, ConversationType.M2M)
    
    async def get_m2c_dialogs(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги manager-to-customer с загрузкой сотрудников"""
        return await self.get_by_conversation_type(db, ConversationType.M2C)
    
    async def get_unknown_dialogs(self, db: AsyncSession) -> List[Dialog]:
        """Получить все диалоги с неизвестным типом с загрузкой сотрудников"""
        return await self.get_by_conversation_type(db, ConversationType.UNKNOWN)
    
    async def get_by_filename(self, db: AsyncSession, filename: str) -> Optional[Dialog]:
        """Получить диалог по имени файла с загрузкой сотрудника"""
        query = select(self.model).options(selectinload(self.model.employee)).where(self.model.filename == filename)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_date_range(
        self, 
        db: AsyncSession, 
        start_date: datetime, 
        end_date: datetime
    ) -> List[Dialog]:
        """Получить диалоги в диапазоне дат записи с загрузкой сотрудников"""
        return await self.get_multi(
            db,
            recording_start_date__gte=start_date,
            recording_end_date__lte=end_date
        )
    
    async def get_by_recording_date(self, db: AsyncSession, date: datetime) -> List[Dialog]:
        """Получить диалоги по дате записи с загрузкой сотрудников"""
        return await self.get_multi(
            db,
            recording_start_date__date=date.date()
        )
    
    async def search_by_filename(self, db: AsyncSession, filename_part: str) -> List[Dialog]:
        """Поиск диалогов по части имени файла с загрузкой сотрудников"""
        return await self.get_multi(db, filename__icontains=filename_part)
    
    async def get_employee_dialogs_by_type(
        self, 
        db: AsyncSession, 
        employee_id: UUID, 
        conversation_type: ConversationType
    ) -> List[Dialog]:
        """Получить диалоги сотрудника определенного типа с загрузкой сотрудников"""
        return await self.get_multi(
            db,
            employee_id=employee_id,
            conversation_type=conversation_type
        )
    
    async def get_recent_dialogs(self, db: AsyncSession, days: int = 7) -> List[Dialog]:
        """Получить диалоги за последние N дней с загрузкой сотрудников"""
        from datetime import timedelta
        cutoff_date = datetime.now() - timedelta(days=days)
        return await self.get_multi(
            db,
            recording_start_date__gte=cutoff_date,
            order_by="-recording_start_date"
        )
    
    async def create(self, db: AsyncSession, obj_in: DialogCreate) -> Dialog:
        """Создать новый диалог с загрузкой сотрудника"""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # Загружаем связанного сотрудника
        query = select(self.model).options(selectinload(self.model.employee)).where(self.model.id == db_obj.id)
        result = await db.execute(query)
        return result.scalar_one()
    
    async def update(self, db: AsyncSession, id: Any, obj_in: DialogUpdate) -> Optional[Dialog]:
        """Обновить диалог с загрузкой сотрудника"""
        db_obj = await self.get(db, id)
        if not db_obj:
            return None
        
        update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # Загружаем связанного сотрудника
        query = select(self.model).options(selectinload(self.model.employee)).where(self.model.id == db_obj.id)
        result = await db.execute(query)
        return result.scalar_one()
    
    async def update_conversation_type(
        self, 
        db: AsyncSession, 
        dialog_id: UUID, 
        conversation_type: ConversationType
    ) -> Optional[Dialog]:
        """Обновить тип разговора с загрузкой сотрудника"""
        result = await self.update_by_field(
            db, 
            "id", 
            dialog_id, 
            {"conversation_type": conversation_type}
        )
        if result:
            # Загружаем связанного сотрудника
            query = select(self.model).options(selectinload(self.model.employee)).where(self.model.id == dialog_id)
            db_result = await db.execute(query)
            return db_result.scalar_one()
        return None
    
    async def update_conversation_data(
        self, 
        db: AsyncSession, 
        dialog_id: UUID, 
        conversation_data: dict
    ) -> Optional[Dialog]:
        """Обновить данные разговора с загрузкой сотрудника"""
        result = await self.update_by_field(
            db, 
            "id", 
            dialog_id, 
            {"conversation": conversation_data}
        )
        if result:
            # Загружаем связанного сотрудника
            query = select(self.model).options(selectinload(self.model.employee)).where(self.model.id == dialog_id)
            db_result = await db.execute(query)
            return db_result.scalar_one()
        return None
    
    async def get_employee_metrics_by_organization(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
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
        organization_id: UUID,
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

    async def get_organization_daily_metrics_chart(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
        metric_types: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[Dict[str, Any]]:
        """Получить метрики организации по дням для построения графика с фильтрацией по метрикам"""
        from app.models.users import Employee
        
        # Строим запрос с выбранными метриками
        select_fields = [
            func.date(Dialog.recording_start_date).label("date")
        ]
        
        for metric_type in metric_types:
            metric_column = getattr(Dialog, metric_type)
            select_fields.append(func.avg(metric_column).label(f"avg_{metric_type}"))
        
        query = select(*select_fields).join(Employee, Dialog.employee_id == Employee.id).where(
            Employee.organization_id == organization_id
        )
        
        # Фильтр по датам
        if start_date:
            query = query.where(Dialog.recording_start_date >= start_date)
        if end_date:
            query = query.where(Dialog.recording_start_date <= end_date)
            
        query = query.group_by(func.date(Dialog.recording_start_date))
        query = query.order_by(func.date(Dialog.recording_start_date))
        
        result = await db.execute(query)
        rows = result.fetchall()
        
        # Логируем для отладки
        from app.core.logging import get_logger
        logger = get_logger(__name__)
        logger.info(f"SQL запрос вернул {len(rows)} строк для метрик {metric_types}")
        for row in rows:
            logger.info(f"Дата: {row.date}, метрики: {[getattr(row, f'avg_{metric}') for metric in metric_types]}")
        
        return rows

    async def get_employee_metrics_by_days(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
        metric_type: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        employee_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Получить метрики сотрудников по дням для построения графика"""
        from app.models.users import Employee
        
        # Выбираем нужную метрику
        metric_column = getattr(Dialog, metric_type)
        
        query = select(
            Employee.id,
            Employee.first_name,
            Employee.last_name,
            func.date(Dialog.recording_start_date).label("date"),
            func.avg(metric_column).label("avg_metric")
        ).join(Employee, Dialog.employee_id == Employee.id).where(
            Employee.organization_id == organization_id
        )
        
        # Фильтр по датам
        if start_date:
            adjusted_start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Dialog.recording_start_date >= adjusted_start_date)
        if end_date:
            adjusted_end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(Dialog.recording_end_date <= adjusted_end_date)
        
        # Фильтр по сотрудникам
        if employee_ids:
            query = query.where(Employee.id.in_(employee_ids))
            
        query = query.group_by(Employee.id, Employee.first_name, Employee.last_name, func.date(Dialog.recording_start_date))
        query = query.order_by(Employee.first_name, Employee.last_name, func.date(Dialog.recording_start_date))
        
        result = await db.execute(query)
        return result.fetchall()

    async def get_organization_average_metrics(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Получить средние метрики организации по всем диалогам"""
        from app.models.users import Employee

        query = select(
            func.avg(Dialog.greeting_farewell_score).label("avg_greeting_farewell"),
            func.avg(Dialog.completeness_score).label("avg_completeness"),
            func.avg(Dialog.tone_score).label("avg_tone"),
            func.avg(Dialog.openness_helpfulness_score).label("avg_openness_helpfulness"),
            func.avg(Dialog.listening_score).label("avg_listening"),
            func.avg(Dialog.empathy_score).label("avg_empathy"),
            func.avg(Dialog.speech_quality_score).label("avg_speech_quality"),
            func.avg(Dialog.response_time_score).label("avg_response_time"),
            func.avg(Dialog.overall_score).label("avg_overall")
        ).join(Employee, Dialog.employee_id == Employee.id).where(
            Employee.organization_id == organization_id
        )
        
        # Фильтр по датам
        if start_date:
            adjusted_start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Dialog.recording_start_date >= adjusted_start_date)
        if end_date:
            adjusted_end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(Dialog.recording_start_date <= adjusted_end_date)
       
        result = await db.execute(query)
        row = result.fetchone()

        if not row:
            return {}
        
        result_dict = {
            "avg_greeting_farewell_score": float(row.avg_greeting_farewell or 0.0),
            "avg_completeness_score": float(row.avg_completeness or 0.0),
            "avg_tone_score": float(row.avg_tone or 0.0),
            "avg_openness_helpfulness_score": float(row.avg_openness_helpfulness or 0.0),
            "avg_listening_score": float(row.avg_listening or 0.0),
            "avg_empathy_score": float(row.avg_empathy or 0.0),
            "avg_speech_quality_score": float(row.avg_speech_quality or 0.0),
            "avg_response_time_score": float(row.avg_response_time or 0.0),
            "avg_overall_score": float(row.avg_overall or 0.0)
        }
        
        return result_dict


# Создаем экземпляр для использования в сервисах
dialog_crud = CRUDDialog(Dialog) 