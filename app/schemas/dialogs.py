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
    conversation: Any = Field(..., description="JSON структура разговора")
    filename: str = Field(..., min_length=1, max_length=500, description="Наименование файла")
    recording_start_date: datetime = Field(..., description="Дата начала записи")
    recording_end_date: datetime = Field(..., description="Дата окончания записи")
    audio_data_id: UUID = Field(..., description="ID аудиоданных")
    audio_data_for_analysis_id: UUID = Field(..., description="ID аудиоданных для анализа")
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
    audio_data_for_analysis_id: Optional[UUID] = Field(None, description="ID аудиоданных для анализа")
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
    # Ослабляем типы для ответа, так как в БД могут быть NULL/строковые JSON
    conversation: Any = Field(..., description="JSON структура разговора")
    audio_data_id: Optional[UUID] = Field(None, description="ID аудиоданных")
    audio_data_for_analysis_id: Optional[UUID] = Field(None, description="ID аудиоданных для анализа")
    dictionaries: Optional[str] = Field("", description="Строка с названиями словарей")
    
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
    audio_data_for_analysis_id: UUID
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


class DictionaryLabel(BaseModel):
    """Элемент метки словаря для оси X"""
    description: str
    color: str


class DialogCountsByDictionariesChartResponse(BaseModel):
    """Схема ответа: количество диалогов по словарям (Chart.js)"""
    labels: List[DictionaryLabel]
    datasets: List[ChartDataset]


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
    conversation_type: ConversationType = Field(..., description="Тип разговора")
    overall_score: Optional[float] = Field(None, description="Итоговая оценка")
    dictionaries: str = Field("", description="Строка с названиями словарей")
    
    model_config = ConfigDict(from_attributes=True)


class DialogsByDictionariesResponse(BaseModel):
    """Схема ответа для диалогов по названиям словарей"""
    id: UUID
    title: str
    description: str
    color: str
    dialogs_count: int


class DialogDictionaryPopulateResponse(BaseModel):
    """Схема ответа для заполнения словарей диалога"""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    added_count: int = Field(..., description="Количество добавленных связей")
    total_found: Optional[int] = Field(None, description="Общее количество найденных словарей")
    found_phrases_count: Optional[int] = Field(None, description="Количество найденных фраз")


class DialogDictionaryPopulateAllResponse(BaseModel):
    """Схема ответа для заполнения словарей всех диалогов"""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    processed_count: int = Field(..., description="Количество обработанных диалогов")
    total_added: int = Field(..., description="Общее количество добавленных связей")
    errors: Optional[List[str]] = Field(None, description="Список ошибок")


class DialogDictionaryClearResponse(BaseModel):
    """Схема ответа для очистки связей диалогов со словарями"""
    success: bool = Field(..., description="Успешность операции")
    message: str = Field(..., description="Сообщение о результате")
    deleted_count: int = Field(..., description="Количество удаленных связей")


class DialogHighlightedResponse(BaseModel):
    """Схема ответа для диалога с подсвеченным текстом"""
    dialog_id: UUID = Field(..., description="ID диалога")
    original_text: str = Field(..., description="Оригинальный текст диалога")
    highlighted_text: str = Field(..., description="Текст диалога с подсвеченными словами")
    conversation_type: ConversationType = Field(..., description="Тип разговора")
    filename: str = Field(..., description="Имя файла")
    recording_start_date: datetime = Field(..., description="Дата начала записи")
    recording_end_date: datetime = Field(..., description="Дата окончания записи")
    was_updated_in_db: bool = Field(False, description="Был ли диалог обновлен в базе данных")
    
    model_config = ConfigDict(from_attributes=True)

class DictionaryWithWordsResponse(BaseModel):
    """Схема ответа для словаря со списком слов"""
    id: UUID
    title: str
    description: str
    color: str
    words: List[str]

    model_config = ConfigDict(from_attributes=True)

