from datetime import datetime
from jose import JWTError, jwt
from typing import Optional

from fastapi import Depends, HTTPException, status, Request, Security
from fastapi.openapi.models import OAuthFlows as OAuthFlowsModel
from fastapi.security.utils import get_authorization_scheme_param
from fastapi.security import (
    SecurityScopes,
    OAuth2
)
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession


from app.core.logging import LoggerMixin
from app.schemas.users import TokenData
from app.core.config import settings
from app.crud.users import user_crud
from app.db.session import get_db


class OAuth2PasswordBearerCookie(OAuth2):
    def __init__(
        self,
        token_url: str,
        scheme_name: str = None,
        scopes: dict = None,
        auto_error: bool = True,
    ):
        if not scopes:
            scopes = {}
        flows = OAuthFlowsModel(password={"tokenUrl": token_url, "scopes": scopes})
        super().__init__(flows=flows, scheme_name=scheme_name, auto_error=auto_error)

    async def __call__(self, request: Request) -> Optional[str]:
        authorization: str = request.cookies.get("Authorization")
        scheme, param = get_authorization_scheme_param(authorization)

        if not authorization or scheme.lower() != "bearer":
            if self.auto_error:
                raise HTTPException(
                    status_code=401,
                    detail="Not authenticated",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            else:
                return None

        return param


security = OAuth2PasswordBearerCookie(token_url=f"{settings.API_PREFIX}/users/login")
log = LoggerMixin()

async def get_current_user(
        security_scopes: SecurityScopes,
        token: str = Depends(security),
        db: AsyncSession = Depends(get_db)

):
    if security_scopes.scopes:
        authenticate_value = f'Bearer scope="{security_scopes.scope_str}"'
    else:
        authenticate_value = f"Bearer"
    log.logger.debug(f'GET CURRENT USER ---> token: {token}')
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": authenticate_value},
    )
    try:
        payload = jwt.decode(token, str(settings.SECRET_KEY), algorithms=["HS256"])
        log.logger.debug(f'GET CURRENT USER ---> payload: {payload}')
        username: str = payload.get("sub")
        log.logger.debug(f'GET CURRENT USER ---> username: {username}')
        if username is None:
            log.logger.error(f'GET CURRENT USER ---> username is None')
            raise credentials_exception
        token_scopes = payload.get("scopes", '')
        token_data = TokenData(scopes=token_scopes, username=username)
    except (JWTError, ValidationError) as e:
        log.logger.error(f'GET CURRENT USER ---> JWTError, ValidationError: {e}')
        raise credentials_exception

    user = await user_crud.get_by_username(db=db, username=token_data.username)
    log.logger.info(f'GET CURRENT USER ---> user: {user.username}')
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Inactive user"
        )
    in_scope = any(x in token_data.scopes for x in security_scopes.scopes)
    log.logger.info(f'GET CURRENT USER ---> token_data.scopes: {token_data.scopes} | security_scopes.scopes: {security_scopes.scopes}')
    if not in_scope:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not enough permissions",
            headers={"WWW-Authenticate": authenticate_value},
        )
    return user
