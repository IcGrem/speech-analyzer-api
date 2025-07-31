from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Response, Security
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi.security import OAuth2PasswordRequestForm

from app.db.session import get_db
from app.crud.users import user_crud
from app.schemas.users import UserResponse, UserCreate, UserUpdate
from app.services.dependencies import get_current_user
from app.core.exceptions import InvalidCredentialsError, UserNotFoundError
from app.core.security import verify_password, create_access_token

router = APIRouter()


@router.post("/login", response_model=UserResponse, description="Авторизация пользователя")
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Авторизация пользователя"""
    user = await user_crud.get_by_username(db, form_data.username)
    if not user:
        raise UserNotFoundError()
    if not verify_password(form_data.password, user.hashed_password):
        raise InvalidCredentialsError()
    access_token = create_access_token(data={"sub": user.username})
    response.set_cookie(
        key="Authorization",
        value=f"Bearer {access_token}",
        httponly=True,
        secure=True,
        samesite="strict"
    )
    return user


@router.post("/logout")
async def logout(response: Response):
    """Выход из системы"""
    response.delete_cookie(key="access_token")
    return {"message": "Выход из системы прошел успешно"}


@router.get("/me", response_model=UserResponse, description="Получение информации о текущем пользователе")
async def get_current_user_info(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator'])
) -> UserResponse:
    """Получение информации о текущем пользователе"""
    return current_user


@router.get("/get-users", response_model=List[UserResponse], description="Получение списка всех пользователей")
async def get_users(
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """Получение списка всех пользователей"""
    return await user_crud.get_all(db)


@router.post("/create-user", response_model=UserResponse, description="Создание нового пользователя")
async def create_user(
    user: UserCreate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Создание нового пользователя"""
    return await user_crud.create(db, obj_in=user)


@router.put("/update-user/{user_id}", response_model=UserResponse, description="Обновление информации о пользователе")
async def update_user(
    user_id: UUID,
    user: UserUpdate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Обновление информации о пользователе"""
    return await user_crud.update(db, user_id, obj_in=user)


@router.delete("/delete-user/{user_id}", response_model=UserResponse, description="Удаление пользователя")
async def delete_user(
    user_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Удаление пользователя"""
    return await user_crud.remove(db, user_id)


@router.get("/get-user-by-id/{user_id}", response_model=UserResponse, description="Получение информации о пользователе по ID")
async def get_user_by_id(
    user_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """Получение информации о пользователе по ID"""
    return await user_crud.get(db, user_id)


@router.get("/search-users", response_model=List[UserResponse], description="Поиск пользователей по имени")
async def search_users(
    name: str,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[UserResponse]:
    """Поиск пользователей по имени"""
    return await user_crud.search_by_name(db, name)

