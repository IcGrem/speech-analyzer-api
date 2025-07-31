from datetime import datetime
from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Ответ для проверки здоровья приложения"""
    status: str
    timestamp: datetime
    database: str
    version: str 