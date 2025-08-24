import os

from typing import List, Any, Annotated, Optional
from pydantic import Field, field_validator, PostgresDsn
from pydantic_settings import BaseSettings
from pathlib import Path

from pygments.lexer import default


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
    COOKIE_SAMESITE: str = Field(default="lax", env="COOKIE_SAMESITE")
    COOKIE_SECURE: bool = Field(default=False, env="COOKIE_SECURE")
    
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
    
    # Voca.tech API
    VOCA_API_KEY: str = Field(env="VOCA_API_KEY")
    
    # Планировщик
    ENABLE_HOURLY_DOWNLOAD: bool = Field(default=False, env="ENABLE_HOURLY_DOWNLOAD")
    
    # Организация по умолчанию
    DEFAULT_ORGANIZATION_ID: str = Field(default="00000000-0000-0000-0000-000000000000", env="DEFAULT_ORGANIZATION_ID")

    # ML-настройки
    # Обработка аудио
    FRAME_RATE: int = 16000
    # минимальная длительность блока с речью, пример 0.5 * 60 = 30 секунд
    MIN_DURATION_DIALOGUE: int = round(0.5 * 60)
    # минимальная длительность паузы между речью, пример 0.34 * 60 = 20 секунд
    MIN_DURATION_PAUSE: int = round(0.34 * 60)

    # папка куда сохраняются дневные аудиозаписи
    FOLDER_W_FULL_AUDIO: str = os.path.join("full_speech_data")
    # папка куда сохраняются блоки для дневных аудио
    FOLDER_W_DIALOGUES: str = os.path.join("dialogues")
    # папка куда сохраняются аудио с разделением на спикеров
    FOLDER_W_DIARIZATION: str = os.path.join("diarization")

    # логгер
    LOGGER_FOLDER: str = os.path.join('app', 'ml', 'logs', 'main')

    # модели
    VAD_MODEL: str = "pyannote/voice-activity-detection"
    TRANSCRIPTION_MODEL: str = "openai/whisper-large-v3"
    DIARIZATION_MODEL: str = "pyannote/speaker-diarization-3.1"

    # подключение к OpenAI
    OPENAI_BASE_URL: str = "https://api.openai.com/v1/"
    OPENAI_MODEL_TYPE: str = "gpt-4o"
    OPENAI_API_KEY: str = Field(default="", env="OPENAI_API_KEY")

    # обработка текста
    uninformative_phrases: Annotated[List[str], Field(default_factory=lambda: [
        'Продолжение следует...',
        'Спасибо за субтитры Алексею Дубровскому.',
        'Субтитры сделал DimaTorzok',
        'Субтитры создавал DimaTorzok',
        'Спасибо.',
        'НЕРАЗБОРЧИВО',
        'Пока.',
        'Это очень хорошо.',
        'Субтитры подогнал «Симон»',
    ])]

    #  минимальный размер длины текста для блока текста
    MIN_CONTENT_LENGTH: int = 100

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings() 