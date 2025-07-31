from typing import List, Any
from pydantic import Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""
    
    # Основные настройки
    PROJECT_NAME: str = "Speech Analyzer API"
    VERSION: str = "1.0.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    API_PREFIX: str = Field(default="/api/v1", env="API_PREFIX")
    
    # Настройки сервера
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # CORS
    ALLOWED_HOSTS: List[str] = Field(default=["*"], env="ALLOWED_HOSTS")
    
    # База данных
    POSTGRES_USER: str = Field(env="POSTGRES_USER")
    POSTGRES_PASSWORD: str = Field(env="POSTGRES_PASSWORD")
    POSTGRES_HOST: str = Field(env="POSTGRES_HOST")
    POSTGRES_PORT: int = Field(default=5432, env="POSTGRES_PORT")
    POSTGRES_DB: str = Field(env="POSTGRES_DB")
    
    ASYNC_DATABASE_URI: str | None = None

    @field_validator("ASYNC_DATABASE_URI", mode='before')
    @classmethod
    def assemble_db_connection(cls, v: str | None, info: Any) -> Any:
        if v:
            return v
        
        # В Pydantic v2 мы получаем доступ к другим значениям через info.data
        values = info.data
        
        return str(PostgresDsn.build(
            scheme="postgresql+asyncpg",
            username=values.get("POSTGRES_USER"),
            password=values.get("POSTGRES_PASSWORD"),
            host=values.get("POSTGRES_HOST"),
            port=int(values.get("POSTGRES_PORT", 5432)),
            path=f"{values.get('POSTGRES_DB', '')}",
        ))
    
    # Redis
    # REDIS_URL: str = Field(default="redis://localhost:6379", env="REDIS_URL")
    
    # JWT
    SECRET_KEY: str = Field(env="SECRET_KEY")
    ALGORITHM: str = Field(default="HS256", env="ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Логирование
    LOG_LEVEL: str = Field(default="INFO", env="LOG_LEVEL")
    LOG_FORMAT: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    
    # Администратор по умолчанию
    ADMIN_USERNAME: str = Field(default="admin", env="ADMIN_USERNAME")
    ADMIN_PASSWORD: str = Field(env="ADMIN_PASSWORD")
    ADMIN_EMAIL: str = Field(default="admin@example.com", env="ADMIN_EMAIL")
    ADMIN_FIRST_NAME: str = Field(default="Администратор", env="ADMIN_FIRST_NAME")
    ADMIN_LAST_NAME: str = Field(default="Системы", env="ADMIN_LAST_NAME")
    
    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 