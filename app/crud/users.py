from typing import List, Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_

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
    
    async def get_by_email(self, db: AsyncSession, email: str) -> Optional[Employee]:
        """Получить сотрудника по email"""
        return await self.get_by_field(db, "email", email)
    
    async def get_by_phone(self, db: AsyncSession, phone: str) -> Optional[Employee]:
        """Получить сотрудника по телефону"""
        return await self.get_by_field(db, "phone", phone)
    
    async def get_by_organization(self, db: AsyncSession, organization_id: UUID) -> List[Employee]:
        """Получить всех сотрудников организации"""
        return await self.get_multi(db, organization_id=organization_id)
    
    async def get_active_employees(self, db: AsyncSession) -> List[Employee]:
        """Получить всех активных сотрудников"""
        return await self.get_multi(db, is_active=True)
    
    async def get_by_position(self, db: AsyncSession, position: str) -> List[Employee]:
        """Получить сотрудников по должности"""
        return await self.get_multi(db, position=position)
    
    async def search_by_name(self, db: AsyncSession, name_part: str) -> List[Employee]:
        """Поиск сотрудников по части имени"""
        query = select(self.model).where(
            or_(
                self.model.first_name.ilike(f'%{name_part}%'),
                self.model.last_name.ilike(f'%{name_part}%')
            )
        )
        result = await db.execute(query)
        return result.scalars().all()
    
    async def deactivate_employee(self, db: AsyncSession, employee_id: UUID) -> Optional[Employee]:
        """Деактивировать сотрудника"""
        return await self.update_by_field(db, "id", employee_id, {"is_active": False})
    
    async def activate_employee(self, db: AsyncSession, employee_id: UUID) -> Optional[Employee]:
        """Активировать сотрудника"""
        return await self.update_by_field(db, "id", employee_id, {"is_active": True})


# Создаем экземпляры для использования в сервисах
user_crud = CRUDUser(User)
organization_crud = CRUDOrganization(Organization)
employee_crud = CRUDEmployee(Employee) 