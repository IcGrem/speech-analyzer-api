from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import random

from app.db.session import get_db
from app.crud.dialogs import dialog_crud
from app.models.dialogs import ConversationType
from app.schemas.dialogs import (
    DialogResponse, 
    DialogCreate, 
    DialogUpdate, 
    DialogList,
    DialogWithEmployee,
    EmployeeMetrics,
    OrganizationDailyMetrics,
    AudioDownloadRequest,
    AudioDownloadResponse,
    EmployeeMetricsChartResponse,
    OrganizationDailyMetricsChartResponse,
    ChartDataset,
    MetricType
)
from app.schemas.users import UserResponse
from app.services.dependencies import get_current_user
from app.services.dialog_service import voca_service
from app.core.exceptions import DialogNotFoundError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/get-audiodata-from-voca", response_model=AudioDownloadResponse, description="Конкурентная загрузка аудиофайлов за указанный период")
async def get_audiodata_from_voca(
    request: AudioDownloadRequest,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator'])
) -> AudioDownloadResponse:
    """
    Конкурентная загрузка аудиофайлов из Voca API за указанный период
    
    Args:
        request: Параметры загрузки (даты и количество одновременных запросов)
        current_user: Текущий пользователь
    
    Returns:
        Результат загрузки с количеством загруженных файлов
    """
    try:
        import time
        start_time = time.time()
        
        logger.info(f"Запуск загрузки аудиофайлов пользователем {current_user.username}")
        
        # Определяем период загрузки
        if request.start_date and request.end_date:
            # Используем переданные даты
            start_dt = datetime.strptime(request.start_date, "%Y-%m-%d %H:%M")
            end_dt = datetime.strptime(request.end_date, "%Y-%m-%d %H:%M")
            period_str = f"{request.start_date} - {request.end_date}"
        else:
            # Используем предыдущий час
            start_dt = None
            end_dt = None
            period_str = "предыдущий час"
        
        # Запускаем загрузку записей
        downloaded_records = await voca_service.download_records(
            start_date=start_dt,
            end_date=end_dt
        )
        
        download_time = time.time() - start_time
        
        # Формируем ответ
        response = AudioDownloadResponse(
            success=True,
            message=f"Успешно загружено {len(downloaded_records)} аудиофайлов за период {period_str} (с соблюдением ограничений API: 30 запросов/мин)",
            downloaded_count=len(downloaded_records),
            total_found=len(downloaded_records),  # В данном случае совпадает, так как API возвращает только доступные записи
            period=period_str,
            download_time=round(download_time, 2)
        )
        
        logger.info(f"Загрузка завершена: {response.downloaded_count} файлов за {response.download_time}с")
        
        return response
        
    except ValueError as e:
        logger.error(f"Ошибка в формате даты: {e}")
        raise HTTPException(
            status_code=400, 
            detail=f"Неверный формат даты. Используйте формат 'YYYY-MM-DD HH:MM': {str(e)}"
        )
    except Exception as e:
        logger.error(f"Ошибка при загрузке аудиофайлов: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Ошибка при загрузке аудиофайлов: {str(e)}"
        )


@router.get("/get-dialogs", response_model=List[DialogList], description="Получение списка всех диалогов")
async def get_dialogs(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogList]:
    """Получение списка всех диалогов"""
    return await dialog_crud.get_all(db)


@router.post("/create-dialog", response_model=DialogResponse, description="Создание нового диалога")
async def create_dialog(
    dialog: DialogCreate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> DialogResponse:
    """Создание нового диалога"""
    return await dialog_crud.create(db, dialog)


@router.get("/get-dialog/{dialog_id}", response_model=DialogWithEmployee, description="Получение диалога по ID")
async def get_dialog(
    dialog_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> DialogWithEmployee:
    """Получение диалога по ID"""
    dialog = await dialog_crud.get(db, dialog_id)
    if not dialog:
        raise DialogNotFoundError()
    return dialog


@router.put("/update-dialog/{dialog_id}", response_model=DialogResponse, description="Обновление диалога")
async def update_dialog(
    dialog_id: UUID,
    dialog: DialogUpdate,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> DialogResponse:
    """Обновление диалога"""
    dialog_obj = await dialog_crud.update(db, dialog_id, dialog)
    if not dialog_obj:
        raise DialogNotFoundError()
    return dialog_obj


@router.delete("/delete-dialog/{dialog_id}", response_model=DialogResponse, description="Удаление диалога")
async def delete_dialog(
    dialog_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin']),
    db: AsyncSession = Depends(get_db)
) -> DialogResponse:
    """Удаление диалога"""
    dialog = await dialog_crud.remove(db, dialog_id)
    if not dialog:
        raise DialogNotFoundError()
    return dialog


@router.get("/get-dialogs-by-employee/{employee_id}", response_model=List[DialogList], description="Получение диалогов сотрудника")
async def get_dialogs_by_employee(
    employee_id: UUID,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogList]:
    """Получение диалогов сотрудника"""
    return await dialog_crud.get_by_employee(db, employee_id)


@router.get("/get-dialogs-by-date-range", response_model=List[DialogList], description="Получение диалогов по диапазону дат")
async def get_dialogs_by_date_range(
    start_date: datetime = Query(..., description="Дата начала"),
    end_date: datetime = Query(..., description="Дата окончания"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogList]:
    """Получение диалогов по диапазону дат"""
    return await dialog_crud.get_by_date_range(db, start_date, end_date)


@router.get("/get-employee-metrics/{organization_id}", response_model=EmployeeMetricsChartResponse, description="Получение метрик сотрудников организации в формате графика")
async def get_employee_metrics(
    organization_id: UUID,
    metric_type: MetricType = Query(..., description="Тип метрики для анализа"),
    employee_ids: Optional[str] = Query(None, description="Список ID сотрудников через запятую"),
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeMetricsChartResponse:
    """Получение метрик сотрудников организации в формате Chart.js с фильтрацией по метрикам и сотрудникам"""
    
    # Логика работы с датами: если start_date и end_date совпадают, добавляем предыдущий день
    adjusted_start_date = start_date
    adjusted_end_date = end_date
    
    if start_date and end_date and start_date.date() == end_date.date():
        # Если даты совпадают, добавляем предыдущий день
        adjusted_start_date = start_date - timedelta(days=1)
    elif start_date:
        # Если передана только start_date, используем её как есть
        adjusted_start_date = start_date
    else:
        # Если даты не переданы, используем None
        adjusted_start_date = None
        adjusted_end_date = None
    
    # Парсим employee_ids из строки
    parsed_employee_ids = None
    if employee_ids:
        try:
            parsed_employee_ids = [UUID(emp_id.strip()) for emp_id in employee_ids.split(',')]
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат ID сотрудников")
    
    # Получаем данные метрик по дням
    metrics_data = await dialog_crud.get_employee_metrics_by_days(
        db, 
        organization_id, 
        metric_type.value,
        adjusted_start_date, 
        adjusted_end_date,
        parsed_employee_ids
    )
    
    # Генерируем случайные цвета для каждого сотрудника
    colors = [
        "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
        "#f43f5e", "#ef4444", "#f97316", "#f59e0b", "#eab308",
        "#84cc16", "#22c55e", "#10b981", "#14b8a6", "#06b6d4",
        "#0ea5e9", "#3b82f6", "#6366f1", "#8b5cf6", "#a855f7"
    ]
    
    # Группируем данные по сотрудникам
    employee_data = {}
    all_dates = set()
    
    for row in metrics_data:
        employee_id = row.id
        employee_name = f"{row.first_name} {row.last_name}"
        date_str = row.date.strftime("%d-%m-%Y")
        metric_value = float(row.avg_metric or 0.0)
        
        all_dates.add(date_str)
        
        if employee_id not in employee_data:
            employee_data[employee_id] = {
                "name": employee_name,
                "color": random.choice(colors),
                "data": {}
            }
        
        employee_data[employee_id]["data"][date_str] = metric_value
    
    # Сортируем даты
    sorted_dates = sorted(all_dates, key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    # Формируем datasets
    datasets = []
    for employee_id, employee_info in employee_data.items():
        data = []
        for date_str in sorted_dates:
            data.append(employee_info["data"].get(date_str, 0.0))
        
        dataset = ChartDataset(
            label=employee_info["name"],
            data=data,
            backgroundColor=employee_info["color"]
        )
        datasets.append(dataset)
    
    return EmployeeMetricsChartResponse(
        labels=sorted_dates,
        datasets=datasets
    )


@router.get("/get-organization-daily-metrics/{organization_id}", response_model=OrganizationDailyMetricsChartResponse, description="Получение дневных метрик организации в формате графика")
async def get_organization_daily_metrics(
    organization_id: UUID,
    metric_types: str = Query(..., description="Список метрик через запятую (greeting_farewell_score,completeness_score,tone_score,openness_helpfulness_score,listening_score,empathy_score,speech_quality_score,response_time_score,overall_score)"),
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> OrganizationDailyMetricsChartResponse:
    """Получение дневных метрик организации в формате Chart.js с фильтрацией по метрикам"""
    
    # Парсим список метрик
    try:
        parsed_metric_types = [metric.strip() for metric in metric_types.split(',')]
        # Валидируем метрики
        valid_metrics = {
            "greeting_farewell_score", "completeness_score", "tone_score", 
            "openness_helpfulness_score", "listening_score", "empathy_score", 
            "speech_quality_score", "response_time_score", "overall_score"
        }
        for metric in parsed_metric_types:
            if metric not in valid_metrics:
                raise HTTPException(status_code=400, detail=f"Неверная метрика: {metric}")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Неверный формат списка метрик: {str(e)}")
    
    # Логика работы с датами
    adjusted_start_date = start_date
    adjusted_end_date = end_date
    
    if start_date and end_date and start_date.date() == end_date.date():
        # Если даты совпадают, добавляем предыдущий день
        adjusted_start_date = start_date - timedelta(days=1)
    elif start_date and not end_date:
        # Если передана только start_date, добавляем предыдущий день
        adjusted_start_date = start_date - timedelta(days=1)
    elif not start_date and end_date:
        # Если передана только end_date, добавляем предыдущий день
        adjusted_end_date = end_date - timedelta(days=1)
    
    # Устанавливаем время для корректной фильтрации
    if adjusted_start_date:
        adjusted_start_date = adjusted_start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if adjusted_end_date:
        adjusted_end_date = adjusted_end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Получаем данные метрик по дням
    logger.info(f"Запрос метрик: org_id={organization_id}, metrics={parsed_metric_types}, start={adjusted_start_date}, end={adjusted_end_date}")
    metrics_data = await dialog_crud.get_organization_daily_metrics_chart(
        db, organization_id, parsed_metric_types, adjusted_start_date, adjusted_end_date
    )
    logger.info(f"Получено {len(metrics_data)} записей метрик")
    
    # Словарь для преобразования названий метрик
    metrics_names = {
        "greeting_farewell_score": "Приветствие и прощание",
        "completeness_score": "Полнота ответа",
        "tone_score": "Тон общения",
        "openness_helpfulness_score": "Открытость и готовность помочь",
        "listening_score": "Умение слушать",
        "empathy_score": "Эмпатия",
        "speech_quality_score": "Грамотная речь",
        "response_time_score": "Время ответа",
        "overall_score": "Итоговая оценка"
    }
    
    # Генерируем случайные цвета для каждой метрики
    colors = [
        "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
        "#f43f5e", "#ef4444", "#f97316", "#f59e0b", "#eab308",
        "#84cc16", "#22c55e", "#10b981", "#14b8a6", "#06b6d4",
        "#0ea5e9", "#3b82f6", "#ccc6f1", "#8b5cf6", "#a855f7"
    ]
    
    # Группируем данные по метрикам
    metric_data = {}
    all_dates = set()
    
    for row in metrics_data:
        date_str = row.date.strftime("%d-%m-%Y")
        all_dates.add(date_str)
        
        for metric_type in parsed_metric_types:
            if metric_type not in metric_data:
                metric_data[metric_type] = {
                    "name": metrics_names[metric_type],
                    "color": random.choice(colors),
                    "data": {}
                }
            
            # Получаем значение метрики
            metric_value = float(getattr(row, f"avg_{metric_type}") or 0.0)
            metric_data[metric_type]["data"][date_str] = metric_value
    
    # Сортируем даты
    sorted_dates = sorted(all_dates, key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    # Формируем datasets
    datasets = []
    for metric_type, metric_info in metric_data.items():
        data = []
        for date_str in sorted_dates:
            data.append(metric_info["data"].get(date_str, 0.0))
        
        dataset = ChartDataset(
            label=metric_info["name"],
            data=data,
            backgroundColor=metric_info["color"]
        )
        datasets.append(dataset)
    
    return OrganizationDailyMetricsChartResponse(
        labels=sorted_dates,
        datasets=datasets
    )


@router.get("/get-organization-daily-metrics-old/{organization_id}", response_model=List[OrganizationDailyMetrics], description="Получение дневных метрик организации (старый формат)")
async def get_organization_daily_metrics_old(
    organization_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[OrganizationDailyMetrics]:
    """Получение суммарных метрик организации по дням с фильтром по датам (старый формат)"""
    metrics_data = await dialog_crud.get_organization_daily_metrics(
        db, organization_id, start_date, end_date
    )
    
    result = []
    for row in metrics_data:
        daily_metrics = OrganizationDailyMetrics(
            date=row.date,
            total_dialogs=row.total_dialogs,
            average_metrics={
                "greeting_farewell_score": float(row.avg_greeting_farewell or 0.0),
                "completeness_score": float(row.avg_completeness or 0.0),
                "tone_score": float(row.avg_tone or 0.0),
                "openness_helpfulness_score": float(row.avg_openness_helpfulness or 0.0),
                "listening_score": float(row.avg_listening or 0.0),
                "empathy_score": float(row.avg_empathy or 0.0),
                "speech_quality_score": float(row.avg_speech_quality or 0.0),
                "response_time_score": float(row.avg_response_time or 0.0),
                "overall_score": float(row.avg_overall or 0.0)
            }
        )
        result.append(daily_metrics)
    
    return result


@router.get("/get-dialogs-by-type/{conversation_type}", response_model=List[DialogList], description="Получение диалогов по типу разговора")
async def get_dialogs_by_type(
    conversation_type: str,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogList]:
    """Получение диалогов по типу разговора"""
    try:
        conv_type = ConversationType(conversation_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Неверный тип разговора")
    
    return await dialog_crud.get_by_conversation_type(db, conv_type)


@router.get("/search-dialogs", response_model=List[DialogList], description="Поиск диалогов по имени файла")
async def search_dialogs(
    filename: str = Query(..., description="Часть имени файла для поиска"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogList]:
    """Поиск диалогов по части имени файла"""
    return await dialog_crud.search_by_filename(db, filename)


@router.get("/get-recent-dialogs", response_model=List[DialogList], description="Получение недавних диалогов")
async def get_recent_dialogs(
    days: int = Query(7, description="Количество дней для поиска"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogList]:
    """Получение диалогов за последние N дней"""
    return await dialog_crud.get_recent_dialogs(db, days)
