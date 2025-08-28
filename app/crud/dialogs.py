from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.users import Employee
from app.models.dialogs import Dialog, ConversationType, DialogDictionary, Dictionary
from app.schemas.dialogs import DialogCreate, DialogUpdate
from app.core.logging import get_logger


class CRUDDialog(CRUDBase[Dialog, DialogCreate, DialogUpdate]):
    """CRUD операции для модели Dialog"""
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[Dialog]:
        """Получить диалог по ID с загрузкой сотрудника"""
        query = (
            select(self.model)
            .options(
                selectinload(self.model.employee).selectinload(Employee.organization)
            )
            .where(self.model.id == id)
        )
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
        query = select(self.model).options(
            selectinload(self.model.employee).selectinload(Employee.organization)
        )
        
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
        query = (
            select(self.model)
            .options(selectinload(self.model.employee).selectinload(Employee.organization))
            .where(self.model.filename == filename)
        )
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
        query = (
            select(self.model)
            .options(selectinload(self.model.employee).selectinload(Employee.organization))
            .where(self.model.id == db_obj.id)
        )
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
        query = (
            select(self.model)
            .options(selectinload(self.model.employee).selectinload(Employee.organization))
            .where(self.model.id == db_obj.id)
        )
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
            query = (
                select(self.model)
                .options(selectinload(self.model.employee).selectinload(Employee.organization))
                .where(self.model.id == dialog_id)
            )
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
            query = (
                select(self.model)
                .options(selectinload(self.model.employee).selectinload(Employee.organization))
                .where(self.model.id == dialog_id)
            )
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
        
        query = query.where(Dialog.conversation_type == 'm2c')

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

        query = query.where(Dialog.conversation_type == 'm2c')

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
        
        query = query.where(Dialog.conversation_type == 'm2c')

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
        query = query.where(Dialog.conversation_type == 'm2c')
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
        query = query.where(Dialog.conversation_type == 'm2c')
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

    async def get_employee_average_metrics_by_organization(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
        metric_types: List[str],
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        employee_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Получить средние метрики всех сотрудников организации с фильтрацией по метрикам и датам"""
        
        # Строим запрос с выбранными метриками
        select_fields = [
            Employee.id,
            Employee.first_name,
            Employee.last_name
        ]
        
        for metric_type in metric_types:
            metric_column = getattr(Dialog, metric_type)
            select_fields.append(func.avg(metric_column).label(f"avg_{metric_type}"))
        
        query = select(*select_fields).join(Employee, Dialog.employee_id == Employee.id).where(
            Employee.organization_id == organization_id
        )
        query = query.where(Dialog.conversation_type == 'm2c')
        # Фильтр по датам
        if start_date:
            adjusted_start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            query = query.where(Dialog.recording_start_date >= adjusted_start_date)
        if end_date:
            adjusted_end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            query = query.where(Dialog.recording_start_date <= adjusted_end_date)

        # Фильтр по сотрудникам
        if employee_ids:
            query = query.where(Employee.id.in_(employee_ids))
            
        query = query.group_by(Employee.id, Employee.first_name, Employee.last_name)
        query = query.order_by(Employee.first_name, Employee.last_name)
        
        result = await db.execute(query)
        return result.fetchall()

    
    async def get_dialogs_with_pagination(
        self,
        db: AsyncSession,
        organization_id: UUID,
        page: int = 1,
        size: int = 10,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        employee_ids: Optional[List[UUID]] = None,
        dictionary_id: Optional[UUID] = None,
        conversation_type: Optional[ConversationType] = None,
        sort_by: str = "recording_start_date",
        sort_order: str = "desc"
    ) -> Dict[str, Any]:
        """Получить диалоги с пагинацией и фильтрами"""
        
        # Базовый запрос для получения диалогов с фильтрами по организации, сотруднику и диапазону дат
        base_query = select(
            Dialog.id,
            Dialog.recording_start_date,
            Dialog.overall_score,
            Dialog.conversation_type,
            Employee.first_name,
            Employee.last_name
        ).join(
            Employee, Dialog.employee_id == Employee.id
        ).where(
            Employee.organization_id == organization_id
        )
        
        # Добавляем JOIN для фильтра по словарю, если он указан
        if dictionary_id:
            base_query = base_query.join(
                DialogDictionary, Dialog.id == DialogDictionary.dialog_id
            ).where(
                DialogDictionary.dictionary_id == dictionary_id
            )
        
        # Применяем фильтры
        if start_date:
            base_query = base_query.where(Dialog.recording_start_date >= start_date)
        if end_date:
            base_query = base_query.where(Dialog.recording_start_date <= end_date)
        if employee_ids:
            base_query = base_query.where(Employee.id.in_(employee_ids))
        if conversation_type:
            base_query = base_query.where(Dialog.conversation_type == conversation_type)
        
        # Запрос для подсчета общего количества
        count_query = select(func.count()).select_from(base_query.subquery())
        total_count_result = await db.execute(count_query)
        total_count = total_count_result.scalar()
        
        # Вычисляем пагинацию
        total_page = (total_count + size - 1) // size  # Округление вверх
        offset = (page - 1) * size
        
        # Применяем сортировку
        if sort_by == "recording_start_date":
            sort_column = Dialog.recording_start_date
        elif sort_by == "overall_score":
            sort_column = Dialog.overall_score
        elif sort_by == "employee_name":
            sort_column = Employee.first_name
        else:
            sort_column = Dialog.recording_start_date  # По умолчанию
        
        if sort_order.lower() == "asc":
            main_query = base_query.order_by(sort_column.asc()).offset(offset).limit(size)
        else:
            main_query = base_query.order_by(sort_column.desc()).offset(offset).limit(size)
        result = await db.execute(main_query)
        rows = result.fetchall()
        
        # Получаем ID диалогов для запроса словарей
        dialog_ids = [row.id for row in rows]
        
        # Запрос для получения словарей для всех диалогов
        dictionaries_query = select(
            DialogDictionary.dialog_id,
            Dictionary.description
        ).join(
            Dictionary, DialogDictionary.dictionary_id == Dictionary.id
        ).where(
            DialogDictionary.dialog_id.in_(dialog_ids)
        )
        dictionaries_result = await db.execute(dictionaries_query)
        dictionaries_rows = dictionaries_result.fetchall()
        
        # Группируем словари по dialog_id
        dialog_dictionaries = {}
        for row in dictionaries_rows:
            if row.dialog_id not in dialog_dictionaries:
                dialog_dictionaries[row.dialog_id] = []
            dialog_dictionaries[row.dialog_id].append(row.description)
        
        # Формируем данные
        data = []
        for row in rows:
            employee_name = f"{row.first_name} {row.last_name}"
            dictionaries = dialog_dictionaries.get(row.id, [])
            data.append({
                "date": row.recording_start_date,
                "employee_name": employee_name,
                "dialog_id": row.id,
                "conversation_type": row.conversation_type,
                "overall_score": float(row.overall_score) if row.overall_score is not None else None,
                "dictionaries": dictionaries
            })
        
        return {
            "total_count": total_count,
            "total_page": total_page,
            "page": page,
            "size": size,
            "data": data
        }

    async def get_dialogs_by_dictionaries(
        self, 
        db: AsyncSession, 
        organization_id: UUID,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        employee_ids: Optional[List[UUID]] = None
    ) -> List[Dict[str, Any]]:
        """Получить количество диалогов по каждому словарю с фильтрами"""
        
        query = select(
            Dictionary.id,
            Dictionary.title,
            Dictionary.description,
            Dictionary.color,
            func.count(Dialog.id).label("dialogs_count")
        ).join(
            DialogDictionary, DialogDictionary.dictionary_id == Dictionary.id
        ).join(
            Dialog, DialogDictionary.dialog_id == Dialog.id
        ).join(
            Employee, Dialog.employee_id == Employee.id
        ).where(
            Employee.organization_id == organization_id,
            Dialog.conversation_type == ConversationType.M2C
        )
        get_logger(__name__).info(f'QUERY - {query}')
        # Применяем фильтры
        if start_date:
            query = query.where(Dialog.recording_start_date >= start_date)
        if end_date:
            query = query.where(Dialog.recording_start_date <= end_date)
        if employee_ids:
            query = query.where(Employee.id.in_(employee_ids))
            
        query = query.group_by(Dictionary.id, Dictionary.title, Dictionary.description, Dictionary.color)
        query = query.order_by(func.count(Dialog.id).desc())
        
        result = await db.execute(query)
        rows = result.fetchall()
        get_logger(__name__).info(f'RESULT - {rows}')
        
        # Преобразуем результат в список словарей
        return [
            {
                "id": row.id,
                "title": row.title,
                "description": row.description,
                "color": row.color,
                "dialogs_count": row.dialogs_count
            }
            for row in rows
        ]

# Создаем экземпляр для использования в сервисах
dialog_crud = CRUDDialog(Dialog) 