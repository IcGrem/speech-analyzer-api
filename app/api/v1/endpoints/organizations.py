from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.crud.users import organization_crud
from app.schemas.users import OrganizationResponse, OrganizationCreate, OrganizationUpdate
from app.services.dependencies import get_current_user
from app.schemas.users import UserResponse

router = APIRouter()


@router.get("/get-organizations", response_model=List[OrganizationResponse], description="Получение списка всех организаций")
async def get_organizations(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[OrganizationResponse]:
    """Получение списка всех организаций"""
    return await organization_crud.get_all(db)


@router.post("/create-organization", response_model=OrganizationResponse, description="Создание новой организации")
async def create_organization(
    organization: OrganizationCreate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """Создание новой организации"""
    return await organization_crud.create(db, organization)


@router.put("/update-organization/{organization_id}", response_model=OrganizationResponse, description="Обновление информации об организации")
async def update_organization(
    organization_id: UUID,
    organization: OrganizationUpdate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """Обновление информации об организации"""
    return await organization_crud.update(db, organization_id, organization)


@router.delete("/delete-organization/{organization_id}", response_model=OrganizationResponse, description="Удаление организации")
async def delete_organization(
    organization_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """Удаление организации"""
    return await organization_crud.remove(db, organization_id)


@router.get("/get-organization-by-id/{organization_id}", response_model=OrganizationResponse, description="Получение информации об организации по ID")
async def get_organization_by_id(
    organization_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> OrganizationResponse:
    """Получение информации об организации по ID"""
    return await organization_crud.get(db, organization_id)


@router.get("/search-organizations", response_model=List[OrganizationResponse], description="Поиск организаций по названию")
async def search_organizations(
    name: str,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[OrganizationResponse]:
    """Поиск организаций по названию"""
    return await organization_crud.search_by_name(db, name) 