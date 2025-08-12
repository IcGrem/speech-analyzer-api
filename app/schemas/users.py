from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field
import enum
from uuid import UUID
from pydantic.config import ConfigDict


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


class TokenData(BaseModel):
    """Схема для токена"""
    scopes: List[str] | str = Field(..., description="Сферы действия токена")
    username: str = Field(..., description="Имя пользователя")


class UserBase(BaseModel):
    """Базовая схема для пользователя"""
    username: str = Field(..., min_length=3, max_length=50, description="Username пользователя")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Имя пользователя")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Фамилия пользователя")
    middle_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Отчество пользователя")
    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Email пользователя")
    phone: Optional[str] = Field(None, pattern=r"^\+?[1-9]\d{1,14}$", description="Телефон пользователя")
    role: UserRole = Field(UserRole.OPERATOR, description="Роль пользователя")


class UserCreate(UserBase):
    """Схема для создания пользователя"""
    hashed_password: str = Field(..., min_length=6, description="Пароль пользователя")


class UserUpdate(BaseModel):
    """Схема для обновления пользователя"""
    username: Optional[str] = Field(None, min_length=3, max_length=50, description="Username пользователя")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Имя пользователя")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Фамилия пользователя")
    middle_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Отчество пользователя")
    email: Optional[str] = Field(None, pattern=r"^[^@]+@[^@]+\.[^@]+$", description="Email пользователя")
    role: Optional[UserRole] = Field(None, description="Роль пользователя")
    is_active: Optional[bool] = Field(None, description="Активен ли пользователь")


class UserResponse(UserBase):
    """Схема ответа для пользователя"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class UserResponseWithToken(BaseModel):
    """Схема ответа для пользователя с токеном"""
    user: UserResponse
    access_token: str = Field(..., description="Токен пользователя")
    
    model_config = ConfigDict(from_attributes=True)


class OrganizationBase(BaseModel):
    """Базовая схема для организации"""
    name: str = Field(..., min_length=1, max_length=200, description="Название организации")
    description: Optional[str] = Field(None, description="Описание организации")
    address: Optional[str] = Field(None, description="Адрес организации")
    phone: Optional[str] = Field(None, description="Телефон организации")
    email: Optional[str] = Field(None, description="Email организации")


class OrganizationCreate(OrganizationBase):
    """Схема для создания организации"""
    pass


class OrganizationUpdate(BaseModel):
    """Схема для обновления организации"""
    name: Optional[str] = Field(None, min_length=1, max_length=200, description="Название организации")
    description: Optional[str] = Field(None, description="Описание организации")
    address: Optional[str] = Field(None, description="Адрес организации")
    phone: Optional[str] = Field(None, description="Телефон организации")
    email: Optional[str] = Field(None, description="Email организации")


class OrganizationResponse(OrganizationBase):
    """Схема ответа для организации"""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeBase(BaseModel):
    """Базовая схема для сотрудника"""
    employee_id: int = Field(..., description="ID сотрудника")
    first_name: str = Field(..., min_length=1, max_length=100, description="Имя сотрудника")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Фамилия сотрудника")
    middle_name: Optional[str] = Field(None, description="Отчество сотрудника")
    position: Optional[str] = Field(None, description="Должность сотрудника")
    phone: Optional[str] = Field(None, description="Телефон сотрудника")
    email: Optional[str] = Field(None, description="Email сотрудника")
    organization_id: UUID = Field(..., description="ID организации")


class EmployeeCreate(EmployeeBase):
    """Схема для создания сотрудника"""
    pass


class EmployeeUpdate(BaseModel):
    """Схема для обновления сотрудника"""
    employee_id: Optional[int] = Field(None, description="ID сотрудника")
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Имя сотрудника")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Фамилия сотрудника")
    middle_name: Optional[str] = Field(None, description="Отчество сотрудника")
    position: Optional[str] = Field(None, description="Должность сотрудника")
    phone: Optional[str] = Field(None, description="Телефон сотрудника")
    email: Optional[str] = Field(None, description="Email сотрудника")
    organization_id: Optional[UUID] = Field(None, description="ID организации")
    is_active: Optional[bool] = Field(None, description="Активен ли сотрудник")


class EmployeeResponse(EmployeeBase):
    """Схема ответа для сотрудника"""
    id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime
    organization: OrganizationResponse
    
    model_config = ConfigDict(from_attributes=True)


class EmployeeList(BaseModel):
    """Схема для списка сотрудников"""
    id: UUID
    employee_id: int
    first_name: str
    last_name: str
    position: Optional[str] = None
    is_active: bool
    organization: OrganizationResponse
    
    model_config = ConfigDict(from_attributes=True) 