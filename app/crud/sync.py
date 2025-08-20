from sqlalchemy.orm import Session
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
# from sqlalchemy.ext.asyncio import AsyncSession
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
    
    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Получить объект по ID"""
        query = select(self.model).where(self.model.id == id)
        result = db.execute(query)
        return result.scalar_one_or_none()
    
    def get_all(self, db: Session) -> List[ModelType]:
        """Получить все объекты"""
        query = select(self.model)
        result = db.execute(query)
        return result.scalars().all()
    
    def get_multi(
        self, 
        db: Session, 
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
        result = db.execute(query)
        return result.scalars().all()
    
    async def create(self, db: Session, obj_in: CreateSchemaType) -> ModelType:
        """Создать новый объект"""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj
    
    def update(
        self,
        db: Session,
        id: Any,
        obj_in: Union[UpdateSchemaType, Dict[str, Any]]
    ) -> Optional[ModelType]:
        """Обновить объект по ID"""
        db_obj = self.get(db, id)
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
        db.commit()
        db.refresh(db_obj)
        return db_obj
    
    def remove(self, db: Session, id: Any) -> Optional[ModelType]:
        """Удалить объект по ID"""
        obj = self.get(db, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
    
    def exists(self, db: Session, id: Any) -> bool:
        """Проверить существование объекта по ID"""
        query = select(self.model).where(self.model.id == id)
        result = db.execute(query)
        return result.scalar_one_or_none() is not None
    
    def count(self, db: Session, **filters) -> int:
        """Подсчитать количество объектов с фильтрацией"""
        query = select(func.count(self.model.id))
        
        for field, value in filters.items():
            if hasattr(self.model, field) and value is not None:
                query = query.where(getattr(self.model, field) == value)
        
        result = db.execute(query)
        return result.scalar()
    
    def get_by_field(
        self, 
        db: Session, 
        field: str, 
        value: Any
    ) -> Optional[ModelType]:
        """Получить объект по произвольному полю"""
        if not hasattr(self.model, field):
            return None
        
        query = select(self.model).where(getattr(self.model, field) == value)
        result = db.execute(query)
        return result.scalar_one_or_none()