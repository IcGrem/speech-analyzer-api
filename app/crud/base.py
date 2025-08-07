from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, delete, func
from sqlalchemy.orm import selectinload
from pydantic import BaseModel

from app.db.base_class import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Универсальный CRUD класс для работы с моделями и Pydantic схемами
    """
    
    def __init__(self, model: Type[ModelType]):
        """
        CRUD объект с методами по умолчанию для Create, Read, Update, Delete (CRUD).
        
        Args:
            model: SQLAlchemy модель
        """
        self.model = model
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Получить объект по ID"""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, db: AsyncSession) -> List[ModelType]:
        """Получить все объекты"""
        query = select(self.model)
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = None,
        **filters
    ) -> List[ModelType]:
        """Получить список объектов с фильтрацией и пагинацией"""
        query = select(self.model)
        
        # Применяем фильтры
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                if field.endswith('__icontains'):
                    # Поддержка поиска по подстроке
                    actual_field = field.replace('__icontains', '')
                    if hasattr(self.model, actual_field):
                        query = query.where(getattr(self.model, actual_field).ilike(f'%{value}%'))
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
    
    async def create(self, db: AsyncSession, obj_in: CreateSchemaType) -> ModelType:
        """Создать новый объект"""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def update(
        self,
        db: AsyncSession,
        id: Any,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> Optional[ModelType]:
        """Обновить объект по ID"""
        db_obj = await self.get(db, id)
        if not db_obj:
            return None
        
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(db_obj, field):
                setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    async def remove(self, db: AsyncSession, id: Any) -> Optional[ModelType]:
        """Удалить объект по ID"""
        obj = await self.get(db, id)
        if obj:
            await db.delete(obj)
            await db.commit()
        return obj
    
    async def exists(self, db: AsyncSession, id: Any) -> bool:
        """Проверить существование объекта по ID"""
        query = select(self.model).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def count(self, db: AsyncSession, **filters) -> int:
        """Подсчитать количество объектов с фильтрацией"""
        query = select(func.count(self.model.id))
        
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.where(getattr(self.model, field) == value)
        
        result = await db.execute(query)
        return result.scalar()
    
    async def get_by_field(
        self, 
        db: AsyncSession, 
        field: str, 
        value: Any
    ) -> Optional[ModelType]:
        """Получить объект по произвольному полю"""
        if not hasattr(self.model, field):
            return None
        
        query = select(self.model).where(getattr(self.model, field) == value)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def update_by_field(
        self,
        db: AsyncSession,
        field: str,
        value: Any,
        update_data: Dict[str, Any]
    ) -> Optional[ModelType]:
        """Обновить объект по произвольному полю"""
        obj = await self.get_by_field(db, field, value)
        if obj:
            # Обновляем объект напрямую
            for field_name, field_value in update_data.items():
                if hasattr(obj, field_name):
                    setattr(obj, field_name, field_value)
            
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            return obj
        return None
    
    async def search_by_name(self, db: AsyncSession, name_part: str) -> List[ModelType]:
        """Поиск по имени (базовая реализация)"""
        # Ищем поля, которые могут содержать имя
        name_fields = ['name', 'first_name', 'last_name', 'username']
        query = select(self.model)
        
        conditions = []
        for field in name_fields:
            if hasattr(self.model, field):
                conditions.append(getattr(self.model, field).ilike(f'%{name_part}%'))
        
        if conditions:
            from sqlalchemy import or_
            query = query.where(or_(*conditions))
        
        result = await db.execute(query)
        return result.scalars().all() 