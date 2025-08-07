from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.users import employee_crud
from app.schemas.users import EmployeeResponse, EmployeeCreate, EmployeeUpdate, EmployeeList
from app.services.dependencies import get_current_user
from app.schemas.users import UserResponse

router = APIRouter()


@router.get("/get-employees", response_model=List[EmployeeResponse], description="Получение списка всех сотрудников")
async def get_employees(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[EmployeeResponse]:
    """Получение списка всех сотрудников"""
    return await employee_crud.get_all(db)


@router.get("/get-employees-list", response_model=List[EmployeeList], description="Получение краткого списка сотрудников")
async def get_employees_list(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[EmployeeList]:
    """Получение краткого списка сотрудников"""
    employees = await employee_crud.get_all(db)
    return [
        EmployeeList(
            id=emp.id,
            first_name=emp.first_name,
            last_name=emp.last_name,
            position=emp.position,
            is_active=emp.is_active,
            organization=emp.organization
        ) for emp in employees
    ]


@router.post("/create-employee", response_model=EmployeeResponse, description="Создание нового сотрудника")
async def create_employee(
    employee: EmployeeCreate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeResponse:
    """Создание нового сотрудника"""
    return await employee_crud.create(db, employee)


@router.put("/update-employee/{employee_id}", response_model=EmployeeResponse, description="Обновление информации о сотруднике")
async def update_employee(
    employee_id: UUID,
    employee: EmployeeUpdate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeResponse:
    """Обновление информации о сотруднике"""
    return await employee_crud.update(db, employee_id, employee)


@router.delete("/delete-employee/{employee_id}", response_model=EmployeeResponse, description="Удаление сотрудника")
async def delete_employee(
    employee_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeResponse:
    """Удаление сотрудника"""
    return await employee_crud.remove(db, employee_id)


@router.get("/get-employee-by-id/{employee_id}", response_model=EmployeeResponse, description="Получение информации о сотруднике по ID")
async def get_employee_by_id(
    employee_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeResponse:
    """Получение информации о сотруднике по ID"""
    return await employee_crud.get(db, employee_id)


@router.get("/search-employees", response_model=List[EmployeeResponse], description="Поиск сотрудников по имени")
async def search_employees(
    name: str,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[EmployeeResponse]:
    """Поиск сотрудников по имени"""
    return await employee_crud.search_by_name(db, name)


@router.get("/get-employees-by-organization/{organization_id}", response_model=List[EmployeeResponse], description="Получение сотрудников организации")
async def get_employees_by_organization(
    organization_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[EmployeeResponse]:
    """Получение сотрудников организации"""
    return await employee_crud.get_by_organization(db, organization_id)


@router.get("/get-active-employees", response_model=List[EmployeeResponse], description="Получение активных сотрудников")
async def get_active_employees(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[EmployeeResponse]:
    """Получение активных сотрудников"""
    return await employee_crud.get_active_employees(db)


@router.get("/get-employees-by-position", response_model=List[EmployeeResponse], description="Получение сотрудников по должности")
async def get_employees_by_position(
    position: str,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[EmployeeResponse]:
    """Получение сотрудников по должности"""
    return await employee_crud.get_by_position(db, position)


@router.put("/activate-employee/{employee_id}", response_model=EmployeeResponse, description="Активация сотрудника")
async def activate_employee(
    employee_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeResponse:
    """Активация сотрудника"""
    return await employee_crud.activate_employee(db, employee_id)


@router.put("/deactivate-employee/{employee_id}", response_model=EmployeeResponse, description="Деактивация сотрудника")
async def deactivate_employee(
    employee_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeResponse:
    """Деактивация сотрудника"""
    return await employee_crud.deactivate_employee(db, employee_id) 