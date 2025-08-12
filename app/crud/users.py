from typing import List, Optional, Any
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.orm import selectinload

from app.crud.base import CRUDBase
from app.models.users import User, Organization, Employee, UserRole
from app.schemas.users import UserCreate, UserUpdate, OrganizationCreate, OrganizationUpdate, EmployeeCreate, EmployeeUpdate


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD операции для модели User"""
    
    async def get_by_username(self, db: AsyncSession, username: str) -> Optional[User]:
        """Получить пользователя по username"""
        return await self.get_by_field(db, "username", username)
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[User]:
        """Получить пользователя по email"""
        return await self.get_by_field(db, "email", email)
    
    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[User]:
        """Получить пользователя по телефону"""
        return await self.get_by_field(db, "phone", phone)
    
    async def get_active_users(self, db: AsyncSession) -> List[User]:
        """Получить всех активных пользователей"""
        return await self.get_multi(db, is_active=True)
    
    async def get_by_role(self, db: AsyncSession, role: UserRole) -> List[User]:
        """Получить пользователей по роли"""
        return await self.get_multi(db, role=role)
    
    async def get_admins(self, db: AsyncSession) -> List[User]:
        """Получить всех администраторов"""
        return await self.get_by_role(db, UserRole.ADMIN)
    
    async def get_operators(self, db: AsyncSession) -> List[User]:
        """Получить всех операторов"""
        return await self.get_by_role(db, UserRole.OPERATOR)
    
    async def update_password(self, db: AsyncSession, user_id: UUID, hashed_password: str) -> Optional[User]:
        """Обновить пароль пользователя"""
        return await self.update_by_field(db, "id", user_id, {"hashed_password": hashed_password})
    
    async def deactivate_user(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Деактивировать пользователя"""
        return await self.update_by_field(db, "id", user_id, {"is_active": False})
    
    async def activate_user(self, db: AsyncSession, user_id: UUID) -> Optional[User]:
        """Активировать пользователя"""
        return await self.update_by_field(db, "id", user_id, {"is_active": True})
    
    async def search_by_name(self, db: AsyncSession, name_part: str) -> List[User]:
        """Поиск пользователей по имени"""
        from sqlalchemy import or_
        query = select(self.model).where(
            or_(
                self.model.first_name.ilike(f'%{name_part}%'),
                self.model.last_name.ilike(f'%{name_part}%'),
                self.model.username.ilike(f'%{name_part}%')
            )
        )
        result = await db.execute(query)
        return result.scalars().all()


class CRUDOrganization(CRUDBase[Organization, OrganizationCreate, OrganizationUpdate]):
    """CRUD операции для модели Organization"""
    
    async def get_by_name(self, db: AsyncSession, name: str) -> Optional[Organization]:
        """Получить организацию по названию"""
        return await self.get_by_field(db, "name", name)
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Organization]:
        """Получить организацию по email"""
        return await self.get_by_field(db, "email", email)
    
    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[Organization]:
        """Получить организацию по телефону"""
        return await self.get_by_field(db, "phone", phone)
    
    async def search_by_name(self, db: AsyncSession, name_part: str) -> List[Organization]:
        """Поиск организаций по части названия"""
        return await self.get_multi(db, name__icontains=name_part)


class CRUDEmployee(CRUDBase[Employee, EmployeeCreate, EmployeeUpdate]):
    """CRUD операции для модели Employee"""
    
    async def get(self, db: AsyncSession, id: Any) -> Optional[Employee]:
        """Получить сотрудника по ID с загрузкой организации"""
        query = select(self.model).options(selectinload(self.model.organization)).where(self.model.id == id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, db: AsyncSession) -> List[Employee]:
        """Получить всех сотрудников с загрузкой организаций"""
        query = select(self.model).options(selectinload(self.model.organization))
        result = await db.execute(query)
        return result.scalars().all()
    
    async def get_multi(
        self, 
        db: AsyncSession, 
        skip: int = 0, 
        limit: int = 100,
        order_by: Optional[str] = None,
        **filters
    ) -> List[Employee]:
        """Получить список сотрудников с фильтрацией, пагинацией и загрузкой организаций"""
        query = select(self.model).options(selectinload(self.model.organization))
        
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
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Employee]:
        """Получить сотрудника по email с загрузкой организации"""
        query = select(self.model).options(selectinload(self.model.organization)).where(self.model.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[Employee]:
        """Получить сотрудника по телефону с загрузкой организации"""
        query = select(self.model).options(selectinload(self.model.organization)).where(self.model.phone == phone)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_employee_id(self, db: AsyncSession, employee_id: int) -> Optional[Employee]:
        """Получить сотрудника по employee_id с загрузкой организации"""
        query = select(self.model).options(selectinload(self.model.organization)).where(self.model.employee_id == employee_id)
        result = await db.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_organization(self, db: AsyncSession, organization_id: UUID) -> List[Employee]:
        """Получить всех сотрудников организации с загрузкой организаций"""
        return await self.get_multi(db, organization_id=organization_id)
    
    async def get_active_employees(self, db: AsyncSession) -> List[Employee]:
        """Получить всех активных сотрудников с загрузкой организаций"""
        return await self.get_multi(db, is_active=True)
    
    async def get_by_position(self, db: AsyncSession, position: str) -> List[Employee]:
        """Получить сотрудников по должности с загрузкой организаций"""
        return await self.get_multi(db, position=position)
    
    async def search_by_name(self, db: AsyncSession, name_part: str) -> List[Employee]:
        """Поиск сотрудников по части имени с загрузкой организаций"""
        query = select(self.model).options(selectinload(self.model.organization)).where(
            or_(
                self.model.first_name.ilike(f'%{name_part}%'),
                self.model.last_name.ilike(f'%{name_part}%')
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def activate_employee(self, db: AsyncSession, employee_id: UUID) -> Optional[Employee]:
        """Активировать сотрудника"""
        result = await self.update_by_field(db, "id", employee_id, {"is_active": True})
        if result:
            # Загружаем связанную организацию
            query = select(self.model).options(selectinload(self.model.organization)).where(self.model.id == employee_id)
            db_result = await db.execute(query)
            return db_result.scalar_one()
        return None
    
    async def deactivate_employee(self, db: AsyncSession, employee_id: UUID) -> Optional[Employee]:
        """Деактивировать сотрудника"""
        result = await self.update_by_field(db, "id", employee_id, {"is_active": False})
        if result:
            # Загружаем связанную организацию
            query = select(self.model).options(selectinload(self.model.organization)).where(self.model.id == employee_id)
            db_result = await db.execute(query)
            return db_result.scalar_one()
        return None
    
    async def create(self, db: AsyncSession, obj_in: EmployeeCreate) -> Employee:
        """Создать нового сотрудника с загрузкой организации"""
        obj_data = obj_in.model_dump()
        db_obj = self.model(**obj_data)
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        
        # Загружаем связанную организацию
        query = select(self.model).options(selectinload(self.model.organization)).where(self.model.id == db_obj.id)
        result = await db.execute(query)
        return result.scalar_one()
    
    async def update(self, db: AsyncSession, id: Any, obj_in: EmployeeUpdate) -> Optional[Employee]:
        """Обновить сотрудника с загрузкой организации"""
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
        
        # Загружаем связанную организацию
        query = select(self.model).options(selectinload(self.model.organization)).where(self.model.id == db_obj.id)
        result = await db.execute(query)
        return result.scalar_one()


# Создаем экземпляры для использования в сервисах
user_crud = CRUDUser(User)
organization_crud = CRUDOrganization(Organization)
employee_crud = CRUDEmployee(Employee) 