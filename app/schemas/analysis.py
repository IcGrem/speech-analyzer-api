from datetime import datetime
from typing import Optional, List
from uuid import UUID
from pydantic import BaseModel, Field


class AnalysisBase(BaseModel):
    """Базовая схема для анализа"""
    title: Optional[str] = Field(None, description="Название анализа")
    description: Optional[str] = Field(None, description="Описание анализа")


class AnalysisCreate(AnalysisBase):
    """Схема для создания анализа"""
    filename: str = Field(..., description="Имя файла")
    file_path: str = Field(..., description="Путь к файлу")
    file_size: int = Field(..., description="Размер файла в байтах")
    status: str = Field("pending", description="Статус анализа")


class AnalysisUpdate(AnalysisBase):
    """Схема для обновления анализа"""
    pass


class AnalysisResult(BaseModel):
    """Результат анализа речи"""
    confidence: float = Field(..., ge=0.0, le=1.0, description="Уверенность в распознавании")
    text: str = Field(..., description="Распознанный текст")
    language: Optional[str] = Field(None, description="Определенный язык")
    duration: Optional[float] = Field(None, description="Длительность аудио в секундах")
    word_count: Optional[int] = Field(None, description="Количество слов")


class AnalysisResponse(AnalysisBase):
    """Схема ответа для анализа"""
    id: UUID
    filename: str
    file_size: int
    status: str
    result: Optional[AnalysisResult] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class AnalysisList(AnalysisBase):
    """Схема для списка анализов"""
    id: UUID
    filename: str
    status: str
    created_at: datetime
    
    class Config:
        from_attributes = True 