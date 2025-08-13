from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class AudioDataBase(BaseModel):
    """Базовая схема для AudioData"""
    audio_data_id: int
    creation_date: datetime
    receive_date: datetime
    end_date: datetime
    duration_sec: int
    employee_id: int
    employee_number: int
    employee_name: str
    employee_position: str
    device_id: int
    device_description: str
    unit_id: int
    unit_name: str
    unit_code: int | None
    is_expired: bool
    filename: str
    is_processed: bool = False


class AudioDataCreate(AudioDataBase):
    """Схема для создания AudioData"""
    pass


class AudioDataUpdate(BaseModel):
    """Схема для обновления AudioData"""
    audio_data_id: Optional[int] = None
    creation_date: Optional[datetime] = None
    receive_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    duration_sec: Optional[int] = None
    employee_id: Optional[int] = None
    employee_number: Optional[int] = None
    employee_name: Optional[str] = None
    employee_position: Optional[str] = None
    device_id: Optional[int] = None
    device_description: Optional[str] = None
    unit_id: Optional[int] = None
    unit_name: Optional[str] = None
    unit_code: Optional[str] = None
    is_expired: Optional[bool] = None
    filename: Optional[str] = None
    is_processed: Optional[bool] = None


class AudioDataResponse(AudioDataBase):
    """Схема для ответа с AudioData"""
    id: int
    
    class Config:
        from_attributes = True


class AudioDataList(BaseModel):
    """Схема для списка AudioData"""
    id: int
    audio_data_id: int
    creation_date: datetime
    employee_name: str
    duration_sec: int
    filename: str
    is_processed: bool
    
    class Config:
        from_attributes = True


class AudioDataStats(BaseModel):
    """Схема для статистики AudioData"""
    total_count: int
    processed_count: int
    unprocessed_count: int
    processed_percentage: float


class AudioDataForAnalysisBase(BaseModel):
    """Базовая схема для AudioDataForAnalysis"""
    employee_id: int
    date: datetime
    full_audio_filename: Optional[str] = None
    is_analyzed: bool = False
    transcribed_text: Optional[str] = None


class AudioDataForAnalysisCreate(AudioDataForAnalysisBase):
    """Схема для создания AudioDataForAnalysis"""
    pass


class AudioDataForAnalysisUpdate(BaseModel):
    """Схема для обновления AudioDataForAnalysis"""
    employee_id: Optional[int] = None
    date: Optional[datetime] = None
    full_audio_filename: Optional[str] = None
    is_analyzed: Optional[bool] = None
    transcribed_text: Optional[str] = None


class AudioDataForAnalysisResponse(AudioDataForAnalysisBase):
    """Схема для ответа с AudioDataForAnalysis"""
    id: int
    
    class Config:
        from_attributes = True
