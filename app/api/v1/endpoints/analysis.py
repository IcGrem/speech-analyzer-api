from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.analysis import AnalysisCreate, AnalysisResponse, AnalysisList
from app.services.analysis_service import AnalysisService
from app.core.exceptions import FileValidationError

router = APIRouter()


@router.post("/", response_model=AnalysisResponse)
async def create_analysis(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db)
) -> AnalysisResponse:
    """Создание нового анализа речи"""
    if not file.filename or not file.filename.lower().endswith(('.wav', '.mp3', '.m4a')):
        raise FileValidationError("Поддерживаются только аудио файлы: .wav, .mp3, .m4a")
    
    service = AnalysisService(db)
    return await service.create_analysis(file)


@router.get("/", response_model=List[AnalysisList])
async def get_analyses(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[AnalysisList]:
    """Получение списка анализов"""
    service = AnalysisService(db)
    return await service.get_analyses(skip=skip, limit=limit)


@router.get("/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> AnalysisResponse:
    """Получение конкретного анализа"""
    service = AnalysisService(db)
    return await service.get_analysis(analysis_id)


@router.delete("/{analysis_id}")
async def delete_analysis(
    analysis_id: UUID,
    db: AsyncSession = Depends(get_db)
) -> dict:
    """Удаление анализа"""
    service = AnalysisService(db)
    await service.delete_analysis(analysis_id)
    return {"message": "Анализ успешно удален"} 