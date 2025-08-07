import os
import uuid
from typing import List, Optional
from uuid import UUID
from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analysis import Analysis
from app.schemas.analysis import AnalysisCreate, AnalysisResponse, AnalysisList
from app.core.exceptions import AnalysisNotFoundError, AudioProcessingError
from app.core.logging import LoggerMixin
from app.services.speech_processor import SpeechProcessor
from app.crud.analysis import analysis_crud


class AnalysisService(LoggerMixin):
    """Сервис для работы с анализом речи"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.speech_processor = SpeechProcessor()
        self.upload_dir = "uploads"
        
        # Создаем директорию для загрузок если её нет
        os.makedirs(self.upload_dir, exist_ok=True)
    
    async def create_analysis(self, file: UploadFile) -> AnalysisResponse:
        """Создание нового анализа"""
        try:
            # Генерируем уникальное имя файла
            file_extension = os.path.splitext(file.filename)[1]
            unique_filename = f"{uuid.uuid4()}{file_extension}"
            file_path = os.path.join(self.upload_dir, unique_filename)
            
            # Сохраняем файл
            content = await file.read()
            with open(file_path, "wb") as f:
                f.write(content)
            
            # Создаем запись в БД через CRUD
            analysis_data = AnalysisCreate(
                filename=file.filename or "unknown",
                file_path=file_path,
                file_size=len(content),
                status="pending"
            )
            
            analysis = await analysis_crud.create(self.db, analysis_data)
            
            # Запускаем обработку в фоне
            await self._process_analysis_background(analysis.id, file_path)
            
            return AnalysisResponse.model_validate(analysis)
            
        except Exception as e:
            self.logger.error(f"Ошибка создания анализа: {e}")
            raise AudioProcessingError(f"Ошибка создания анализа: {str(e)}")
    
    async def get_analyses(self, skip: int = 0, limit: int = 100) -> List[AnalysisList]:
        """Получение списка анализов"""
        analyses = await analysis_crud.get_multi(
            self.db, 
            skip=skip, 
            limit=limit, 
            order_by="-created_at"
        )
        
        return [AnalysisList.model_validate(analysis) for analysis in analyses]
    
    async def get_analysis(self, analysis_id: UUID) -> AnalysisResponse:
        """Получение конкретного анализа"""
        analysis = await analysis_crud.get(self.db, analysis_id)
        
        if not analysis:
            raise AnalysisNotFoundError(f"Анализ с ID {analysis_id} не найден")
        
        return AnalysisResponse.model_validate(analysis)
    
    async def delete_analysis(self, analysis_id: UUID) -> None:
        """Удаление анализа"""
        analysis = await analysis_crud.get(self.db, analysis_id)
        
        if not analysis:
            raise AnalysisNotFoundError(f"Анализ с ID {analysis_id} не найден")
        
        # Удаляем файл
        if os.path.exists(analysis.file_path):
            os.remove(analysis.file_path)
        
        # Удаляем запись из БД через CRUD
        await analysis_crud.remove(self.db, analysis_id)
    
    async def _process_analysis_background(self, analysis_id: UUID, file_path: str) -> None:
        """Обработка анализа в фоновом режиме"""
        try:
            # Используем новый метод SpeechProcessor для обработки с обновлением БД
            await self.speech_processor.process_audio_with_db_update(file_path, analysis_id, self.db)
            
        except Exception as e:
            self.logger.error(f"Ошибка обработки анализа {analysis_id}: {e}")
            await analysis_crud.update_status(self.db, analysis_id, "failed") 