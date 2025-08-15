import enum
from datetime import datetime
from pydantic import BaseModel, Field
from pydantic.config import ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID

from app.schemas.users import EmployeeResponse


class ConversationType(str, enum.Enum):
    M2M = "m2m"  # manager to manager
    M2C = "m2c"  # manager to customer
    UNKNOWN = "unknown"


class MetricType(str, enum.Enum):
    GREETING_FAREWELL = "greeting_farewell_score"
    COMPLETENESS = "completeness_score"
    TONE = "tone_score"
    OPENNESS_HELPFULNESS = "openness_helpfulness_score"
    LISTENING = "listening_score"
    EMPATHY = "empathy_score"
    SPEECH_QUALITY = "speech_quality_score"
    RESPONSE_TIME = "response_time_score"
    OVERALL = "overall_score"


class DialogBase(BaseModel):
    """Базовая схема для диалога"""
    employee_id: UUID = Field(..., description="ID сотрудника")
    conversation_type: ConversationType = Field(ConversationType.UNKNOWN, description="Тип разговора")
    conversation: Dict[str, Any] = Field(..., description="JSON структура разговора")
    filename: str = Field(..., min_length=1, max_length=500, description="Наименование файла")
    recording_start_date: datetime = Field(..., description="Дата начала записи")
    recording_end_date: datetime = Field(..., description="Дата окончания записи")
    audio_data_id: UUID = Field(..., description="ID аудиоданных")
    dictionaries: str = Field(..., description="Строка с названиями словарей")
    
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
    employee_id: Optional[UUID] = Field(None, description="ID сотрудника")
    conversation_type: Optional[ConversationType] = Field(None, description="Тип разговора")
    conversation: Optional[Dict[str, Any]] = Field(None, description="JSON структура разговора")
    filename: Optional[str] = Field(None, min_length=1, max_length=500, description="Наименование файла")
    recording_start_date: Optional[datetime] = Field(None, description="Дата начала записи")
    recording_end_date: Optional[datetime] = Field(None, description="Дата окончания записи")
    audio_data_id: Optional[UUID] = Field(None, description="ID аудиоданных")
    dictionaries: Optional[str] = Field(None, description="Строка с названиями словарей")
    
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
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class DialogWithEmployee(DialogResponse):
    """Схема диалога с информацией о сотруднике"""
    employee: "EmployeeResponse"  # Импортируется из users.py
    
    model_config = ConfigDict(from_attributes=True)


class DialogList(BaseModel):
    """Схема для списка диалогов"""
    id: UUID
    employee_id: UUID
    conversation_type: ConversationType
    filename: str
    recording_start_date: datetime
    recording_end_date: datetime
    audio_data_id: UUID
    dictionaries: str
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


class AudioDownloadRequest(BaseModel):
    """Модель запроса на загрузку аудиофайлов"""
    start_date: Optional[str] = None
    end_date: Optional[str] = None


class AudioDownloadResponse(BaseModel):
    """Модель ответа на загрузку аудиофайлов"""
    success: bool
    message: str
    downloaded_count: int
    total_found: int
    period: str
    download_time: float





class ChartDataset(BaseModel):
    """Схема для набора данных графика"""
    label: str
    data: List[float]
    backgroundColor: str


class EmployeeMetricsChartResponse(BaseModel):
    """Схема ответа для метрик сотрудников в формате Chart.js"""
    labels: List[str]
    datasets: List[ChartDataset]


class OrganizationDailyMetricsChartResponse(BaseModel):
    """Схема ответа для дневных метрик организации в формате Chart.js"""
    labels: List[str]
    datasets: List[ChartDataset]


class AverageMetricScore(BaseModel):
    """Схема для средней оценки метрики"""
    title: str
    score: float


class OrganizationAverageMetricsResponse(BaseModel):
    """Схема ответа для средних метрик организации"""
    average_scores: Dict[str, AverageMetricScore]
    graphic: OrganizationDailyMetricsChartResponse


class PaginatedResponse(BaseModel):
    """Схема пагинированного ответа"""
    total_count: int = Field(..., description="Общее количество записей")
    total_page: int = Field(..., description="Общее количество страниц")
    page: int = Field(..., description="Номер текущей страницы")
    size: int = Field(..., description="Количество записей на странице")
    data: List[Dict[str, Any]] = Field(..., description="Список объектов")


class DialogListItem(BaseModel):
    """Схема элемента списка диалогов для пагинации"""
    date: datetime = Field(..., description="Дата начала записи")
    employee_name: str = Field(..., description="ФИО сотрудника")
    dialog_id: UUID = Field(..., description="ID диалога")
    overall_score: Optional[float] = Field(None, description="Итоговая оценка")
    dictionaries: str = Field("", description="Строка с названиями словарей")
    
    model_config = ConfigDict(from_attributes=True)
