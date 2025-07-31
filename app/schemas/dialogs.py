import enum
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import Optional, Dict, Any
from uuid import UUID

from app.schemas.users import EmployeeResponse


class ConversationType(str, enum.Enum):
    M2M = "m2m"  # manager to manager
    M2C = "m2c"  # manager to customer
    UNKNOWN = "unknown"


class DialogBase(BaseModel):
    """Базовая схема для диалога"""
    employee_id: int = Field(..., description="ID сотрудника")
    conversation_type: ConversationType = Field(ConversationType.UNKNOWN, description="Тип разговора")
    conversation: Dict[str, Any] = Field(..., description="JSON структура разговора")
    filename: str = Field(..., min_length=1, max_length=500, description="Наименование файла")
    recording_start_date: datetime = Field(..., description="Дата начала записи")
    recording_end_date: datetime = Field(..., description="Дата окончания записи")
    
    # Метрики диалога
    greeting_farewell_score: Optional[float] = Field(0.0, ge=0.0, description="Приветствие и прощание")
    completeness_score: Optional[float] = Field(0.0, ge=0.0, description="Полнота ответа")
    tone_score: Optional[float] = Field(0.0, ge=0.0, description="Тон общения")
    openness_helpfulness_score: Optional[float] = Field(0.0, ge=0.0, description="Открытость и готовность помочь")
    listening_score: Optional[float] = Field(0.0, ge=0.0, description="Умение слушать")
    empathy_score: Optional[float] = Field(0.0, ge=0.0, description="Эмпатия")
    speech_quality_score: Optional[float] = Field(0.0, ge=0.0, description="Грамотная речь")
    response_time_score: Optional[float] = Field(0.0, ge=0.0, description="Время ответа")
    overall_score: Optional[float] = Field(0.0, ge=0.0, description="Итоговая оценка")


class DialogCreate(DialogBase):
    """Схема для создания диалога"""
    pass


class DialogUpdate(BaseModel):
    """Схема для обновления диалога"""
    employee_id: Optional[int] = Field(None, description="ID сотрудника")
    conversation_type: Optional[ConversationType] = Field(None, description="Тип разговора")
    conversation: Optional[Dict[str, Any]] = Field(None, description="JSON структура разговора")
    filename: Optional[str] = Field(None, min_length=1, max_length=500, description="Наименование файла")
    recording_start_date: Optional[datetime] = Field(None, description="Дата начала записи")
    recording_end_date: Optional[datetime] = Field(None, description="Дата окончания записи")
    
    # Метрики диалога
    greeting_farewell_score: Optional[float] = Field(None, ge=0.0, description="Приветствие и прощание")
    completeness_score: Optional[float] = Field(None, ge=0.0, description="Полнота ответа")
    tone_score: Optional[float] = Field(None, ge=0.0, description="Тон общения")
    openness_helpfulness_score: Optional[float] = Field(None, ge=0.0, description="Открытость и готовность помочь")
    listening_score: Optional[float] = Field(None, ge=0.0, description="Умение слушать")
    empathy_score: Optional[float] = Field(None, ge=0.0, description="Эмпатия")
    speech_quality_score: Optional[float] = Field(None, ge=0.0, description="Грамотная речь")
    response_time_score: Optional[float] = Field(None, ge=0.0, description="Время ответа")
    overall_score: Optional[float] = Field(None, ge=0.0, description="Итоговая оценка")


class DialogResponse(DialogBase):
    """Схема ответа для диалога"""
    id: int
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DialogWithEmployee(DialogResponse):
    """Схема диалога с информацией о сотруднике"""
    employee: "EmployeeResponse"  # Импортируется из users.py
    
    model_config = ConfigDict(from_attributes=True)


class DialogList(BaseModel):
    """Схема для списка диалогов"""
    id: int
    employee_id: int
    conversation_type: ConversationType
    filename: str
    recording_start_date: datetime
    recording_end_date: datetime
    created_at: datetime
    
    # Метрики диалога
    greeting_farewell_score: Optional[float] = None
    completeness_score: Optional[float] = None
    tone_score: Optional[float] = None
    openness_helpfulness_score: Optional[float] = None
    listening_score: Optional[float] = None
    empathy_score: Optional[float] = None
    speech_quality_score: Optional[float] = None
    response_time_score: Optional[float] = None
    overall_score: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


# Схемы для метрик
class DialogMetrics(BaseModel):
    """Схема для метрик диалога"""
    greeting_farewell_score: float = Field(..., ge=0.0, description="Приветствие и прощание")
    completeness_score: float = Field(..., ge=0.0, description="Полнота ответа")
    tone_score: float = Field(..., ge=0.0, description="Тон общения")
    openness_helpfulness_score: float = Field(..., ge=0.0, description="Открытость и готовность помочь")
    listening_score: float = Field(..., ge=0.0, description="Умение слушать")
    empathy_score: float = Field(..., ge=0.0, description="Эмпатия")
    speech_quality_score: float = Field(..., ge=0.0, description="Грамотная речь")
    response_time_score: float = Field(..., ge=0.0, description="Время ответа")
    overall_score: float = Field(..., ge=0.0, description="Итоговая оценка")


class EmployeeMetrics(BaseModel):
    """Схема для метрик сотрудника"""
    employee_id: UUID
    employee_name: str
    metrics: DialogMetrics
    dialog_count: int


class OrganizationDailyMetrics(BaseModel):
    """Схема для дневных метрик организации"""
    date: datetime
    total_dialogs: int
    average_metrics: DialogMetrics