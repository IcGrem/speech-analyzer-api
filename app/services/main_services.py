import logging
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.security import get_password_hash
from app.crud.users import user_crud
from app.models.users import User, UserRole
from app.schemas.users import UserCreate
from app.core.exceptions import UserAlreadyExistsError
from app.db.session import async_session

logger = logging.getLogger(__name__)


async def create_default_admin(db: AsyncSession) -> Optional[User]:
    """
    Создание учётной записи администратора по умолчанию
    
    Args:
        db: Сессия базы данных
        
    Returns:
        User: Созданный пользователь-администратор или None если уже существует
        
    Raises:
        UserAlreadyExistsError: Если пользователь с таким username уже существует
    """
    try:
        # Проверяем, существует ли уже администратор с таким username
        existing_admin = await user_crud.get_by_username(db, settings.ADMIN_USERNAME)
        if existing_admin:
            logger.info(f"Администратор с username '{settings.ADMIN_USERNAME}' уже существует")
            return existing_admin
        
        # Проверяем, что пароль администратора задан
        if not settings.ADMIN_PASSWORD:
            logger.error("Пароль администратора не задан в конфигурации")
            raise ValueError("ADMIN_PASSWORD не задан в конфигурации")
        
        # Создаем данные для нового администратора
        admin_data = UserCreate(
            username=settings.ADMIN_USERNAME,
            email=settings.ADMIN_EMAIL,
            first_name=settings.ADMIN_FIRST_NAME,
            last_name=settings.ADMIN_LAST_NAME,
            role=UserRole.ADMIN,
            hashed_password=get_password_hash(settings.ADMIN_PASSWORD)
        )
        
        # Создаем пользователя
        admin_user = await user_crud.create(db, obj_in=admin_data)
        
        logger.info(f"Создан администратор по умолчанию: {admin_user.username}")
        return admin_user
        
    except Exception as e:
        logger.error(f"Ошибка при создании администратора по умолчанию: {str(e)}")
        raise


async def ensure_admin_exists(db: AsyncSession) -> User:
    """
    Гарантирует существование администратора в системе.
    Если администратор не существует, создает его.
    
    Args:
        db: Сессия базы данных
        
    Returns:
        User: Существующий или созданный администратор
    """
    try:
        # Проверяем, есть ли хотя бы один администратор
        admins = await user_crud.get_admins(db)
        
        if admins:
            logger.info(f"Найдено {len(admins)} администраторов в системе")
            return admins[0]
        
        # Если администраторов нет, создаем по умолчанию
        logger.info("Администраторы не найдены, создаем администратора по умолчанию")
        return await create_default_admin(db)
        
    except Exception as e:
        logger.error(f"Ошибка при проверке/создании администратора: {str(e)}")
        raise


async def reset_admin_password(db: AsyncSession, new_password: str) -> Optional[User]:
    """
    Сброс пароля администратора по умолчанию
    
    Args:
        db: Сессия базы данных
        new_password: Новый пароль
        
    Returns:
        User: Обновленный пользователь-администратор
    """
    try:
        admin = await user_crud.get_by_username(db, settings.ADMIN_USERNAME)
        if not admin:
            logger.warning(f"Администратор с username '{settings.ADMIN_USERNAME}' не найден")
            return None
        
        # Хешируем новый пароль
        hashed_password = get_password_hash(new_password)
        
        # Обновляем пароль
        updated_admin = await user_crud.update_password(db, admin.id, hashed_password)
        
        logger.info(f"Пароль администратора '{settings.ADMIN_USERNAME}' успешно обновлен")
        return updated_admin
        
    except Exception as e:
        logger.error(f"Ошибка при сбросе пароля администратора: {str(e)}")
        raise 