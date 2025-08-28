from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Security, Query
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
import random

from app.db.session import get_db
from app.crud.dialogs import dialog_crud
from app.crud.audio_data import audio_data_crud
from app.models.dialogs import ConversationType
from app.schemas.dialogs import (
    DialogResponse, 
    DialogCreate, 
    DialogUpdate, 
    DialogList,
    DialogWithEmployee,
    DialogsByDictionariesListResponse,
    DialogsByDictionariesResponse,
    EmployeeMetrics,
    OrganizationDailyMetrics,
    AudioDownloadRequest,
    AudioDownloadResponse,
    EmployeeMetricsChartResponse,
    OrganizationDailyMetricsChartResponse,
    ChartDataset,
    MetricType,
    OrganizationAverageMetricsResponse,
    AverageMetricScore,
    PaginatedResponse
)
from app.schemas.audio_data import AudioDataList, AudioDataStats
from app.schemas.users import UserResponse
from app.services.dependencies import get_current_user
from app.services.dialog_service import voca_service, audio_processor
from app.core.exceptions import DialogNotFoundError
from app.core.logging import get_logger

router = APIRouter()
logger = get_logger(__name__)


@router.post("/get-audiodata-from-voca", response_model=AudioDownloadResponse, description="Конкурентная загрузка аудиофайлов за указанный период")
async def get_audiodata_from_voca(
    request: AudioDownloadRequest,
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
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
            end_date=end_dt,
            db=db
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


@router.get("/get-dialogs/{organization_id}", response_model=PaginatedResponse, description="Получение списка диалогов с пагинацией и фильтрами")
async def get_dialogs(
    organization_id: UUID,
    page: int = Query(1, ge=1, description="Номер страницы"),
    size: int = Query(10, ge=1, le=100, description="Количество записей на странице"),
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    dictionary_id: Optional[UUID] = Query(None, description="ID словаря"),
    conversation_type: Optional[ConversationType] = Query(None, description="Тип разговора (m2c, m2m)"),
    employee_ids: Optional[str] = Query(None, description="Список ID сотрудников через запятую"),
    sort_by: str = Query("recording_start_date", description="Поле для сортировки (recording_start_date, overall_score, employee_name)"),
    sort_order: str = Query("desc", description="Порядок сортировки (asc, desc)"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> PaginatedResponse:
    """Получение списка диалогов с пагинацией и фильтрами"""
    
    # Парсим employee_ids из строки
    parsed_employee_ids = None
    if employee_ids:
        try:
            parsed_employee_ids = [UUID(emp_id.strip()) for emp_id in employee_ids.split(',')]
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат ID сотрудников")
    
    # Валидируем параметры сортировки
    valid_sort_fields = {"recording_start_date", "overall_score", "employee_name"}
    if sort_by not in valid_sort_fields:
        raise HTTPException(status_code=400, detail=f"Неверное поле для сортировки. Допустимые значения: {', '.join(valid_sort_fields)}")
    
    valid_sort_orders = {"asc", "desc"}
    if sort_order.lower() not in valid_sort_orders:
        raise HTTPException(status_code=400, detail="Неверный порядок сортировки. Допустимые значения: asc, desc")
    
    # Получаем данные с пагинацией
    result = await dialog_crud.get_dialogs_with_pagination(
        db=db,
        organization_id=organization_id,
        page=page,
        size=size,
        start_date=start_date,
        end_date=end_date,
        dictionary_id=dictionary_id,
        conversation_type=conversation_type,
        employee_ids=parsed_employee_ids,
        sort_by=sort_by,
        sort_order=sort_order.lower()
    )
    
    return PaginatedResponse(**result)


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
    logger.info(f'METRIC DATA - {metrics_data}')
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
        metric_value = float(row.avg_metric or 0.01)
        
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
            value = employee_info["data"].get(date_str, 0.01)
            data.append(round(value, 2))
        
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
    
    # Словарь для преобразования названий метрик и их цвета
    metrics_names_and_colors = {
        "greeting_farewell_score": {
            "title": "Приветствие и прощание",
            "color": "#0004FFFF"
        },
        "completeness_score": {
            "title": "Полнота ответа",
            "color": "#5D1FF0FF"
        },
        "tone_score": {
            "title": "Тон общения",
            "color": "#F12EE8FF"
        },
        "openness_helpfulness_score": {
            "title": "Открытость и готовность помочь",
            "color": "#39F180FF"
        },
        "listening_score": {
            "title": "Умение слушать",
            "color": "#FBFF2BFF"
        },
        "empathy_score": {
            "title": "Эмпатия",
            "color": "#FF6B35FF"
        },
        "speech_quality_score": {
            "title": "Грамотная речь",
            "color": "#2EE4F1FF"
        },
        "response_time_score": {
            "title": "Время ответа",
            "color": "#C75F5FFF"
        },
        "overall_score": {
            "title": "Итоговая оценка",
            "color": "#FF1313FF"
        }
    }
    
    # Группируем данные по метрикам
    metric_data = {}
    all_dates = set()
    
    for row in metrics_data:
        date_str = row.date.strftime("%d-%m-%Y")
        all_dates.add(date_str)
        
        for metric_type in parsed_metric_types:
            if metric_type not in metric_data:
                metric_data[metric_type] = {
                    "name": metrics_names_and_colors[metric_type]["title"],
                    "color": metrics_names_and_colors[metric_type]["color"],
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
            value = metric_info["data"].get(date_str, 0.0)
            data.append(round(value, 2))
        
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


@router.get("/get-organization-average-metrics/{organization_id}", response_model=OrganizationAverageMetricsResponse, description="Получение средних метрик организации")
async def get_organization_average_metrics(
    organization_id: UUID,
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> OrganizationAverageMetricsResponse:
    """Получение средних метрик организации по всем диалогам с фильтром по датам"""
    
    # Словарь для преобразования названий метрик и их цвета
    metrics_names_and_colors = {
        "greeting_farewell_score": {
            "title": "Приветствие и прощание",
            "color": "#0004FFFF"
        },
        "completeness_score": {
            "title": "Полнота ответа",
            "color": "#5D1FF0FF"
        },
        "tone_score": {
            "title": "Тон общения",
            "color": "#F12EE8FF"
        },
        "openness_helpfulness_score": {
            "title": "Открытость и готовность помочь",
            "color": "#39F180FF"
        },
        "listening_score": {
            "title": "Умение слушать",
            "color": "#FBFF2BFF"
        },
        "empathy_score": {
            "title": "Эмпатия",
            "color": "#FF6B35FF"
        },
        "speech_quality_score": {
            "title": "Грамотная речь",
            "color": "#2EE4F1FF"
        },
        "response_time_score": {
            "title": "Время ответа",
            "color": "#C75F5FFF"
        },
        "overall_score": {
            "title": "Итоговая оценка",
            "color": "#FF1313FF"
        }
    }
    
    # Получаем средние метрики
    logger.info(f"Запрос средних метрик для организации {organization_id}, start_date={start_date}, end_date={end_date}")
    average_metrics = await dialog_crud.get_organization_average_metrics(
        db, organization_id, start_date, end_date
    )
    
    logger.info(f"Получены средние метрики из CRUD: {average_metrics}")
    
    # Формируем average_scores
    average_scores = {}
    logger.info(f"Ключи в average_metrics: {list(average_metrics.keys())}")
    for metric_key, metric_info in metrics_names_and_colors.items():
        avg_key = f"avg_{metric_key}"
        avg_value = average_metrics.get(avg_key, 0.0)
        logger.info(f"Метрика {metric_key} (ключ {avg_key}): avg_value={avg_value}")
        average_scores[metric_key] = AverageMetricScore(
            title=metric_info["title"],
            score=round(avg_value, 2)
        )
    
    # Получаем данные для графика (используем все метрики)
    all_metric_types = list(metrics_names_and_colors.keys())
    
    # Логика работы с датами для графика
    adjusted_start_date = start_date
    adjusted_end_date = end_date
    
    if start_date and end_date and start_date.date() == end_date.date():
        adjusted_start_date = start_date - timedelta(days=1)
    elif start_date and not end_date:
        adjusted_start_date = start_date - timedelta(days=1)
    elif not start_date and end_date:
        adjusted_end_date = end_date - timedelta(days=1)
    
    # Устанавливаем время для корректной фильтрации
    if adjusted_start_date:
        adjusted_start_date = adjusted_start_date.replace(hour=0, minute=0, second=0, microsecond=0)
    if adjusted_end_date:
        adjusted_end_date = adjusted_end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
    
    # Получаем данные метрик по дням для графика
    metrics_data = await dialog_crud.get_organization_daily_metrics_chart(
        db, organization_id, all_metric_types, adjusted_start_date, adjusted_end_date
    )
    
    # Группируем данные по метрикам
    metric_data = {}
    all_dates = set()
    
    for row in metrics_data:
        date_str = row.date.strftime("%d-%m-%Y")
        all_dates.add(date_str)
        
        for metric_type in all_metric_types:
            if metric_type not in metric_data:
                metric_data[metric_type] = {
                    "name": metrics_names_and_colors[metric_type]["title"],
                    "color": metrics_names_and_colors[metric_type]["color"],
                    "data": {}
                }
            
            # Получаем значение метрики
            metric_value = float(getattr(row, f"avg_{metric_type}") or 0.0)
            metric_data[metric_type]["data"][date_str] = metric_value
    
    # Сортируем даты
    sorted_dates = sorted(all_dates, key=lambda x: datetime.strptime(x, "%d-%m-%Y"))
    
    # Формируем datasets для графика
    datasets = []
    for metric_type, metric_info in metric_data.items():
        data = []
        for date_str in sorted_dates:
            value = metric_info["data"].get(date_str, 0.0)
            data.append(round(value, 2))
        
        dataset = ChartDataset(
            label=metric_info["name"],
            data=data,
            backgroundColor=metric_info["color"]
        )
        datasets.append(dataset)
    
    # Формируем график
    graphic = OrganizationDailyMetricsChartResponse(
        labels=sorted_dates,
        datasets=datasets
    )
    
    return OrganizationAverageMetricsResponse(
        average_scores=average_scores,
        graphic=graphic
    )


@router.get("/get-employee-average-metrics/{organization_id}", response_model=EmployeeMetricsChartResponse, description="Получение средних метрик всех сотрудников организации в формате графика")
async def get_employee_average_metrics(
    organization_id: UUID,
    metric_types: str = Query(..., description="Список метрик через запятую (greeting_farewell_score,completeness_score,tone_score,openness_helpfulness_score,listening_score,empathy_score,speech_quality_score,response_time_score,overall_score)"),
    employee_ids: Optional[str] = Query(None, description="Список ID сотрудников через запятую"),
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> EmployeeMetricsChartResponse:
    """Получение средних метрик всех сотрудников организации в формате Chart.js с фильтрацией по метрикам и датам"""
    
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
    
    # Парсим employee_ids из строки
    parsed_employee_ids = None
    if employee_ids:
        try:
            parsed_employee_ids = [UUID(emp_id.strip()) for emp_id in employee_ids.split(',')]
        except ValueError:
            raise HTTPException(status_code=400, detail="Неверный формат ID сотрудников")
    
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
    
    # Получаем данные средних метрик сотрудников
    logger.info(f"Запрос средних метрик сотрудников для организации {organization_id}, metrics={parsed_metric_types}, start_date={start_date}, end_date={end_date}")
    employees_data = await dialog_crud.get_employee_average_metrics_by_organization(
        db,
        organization_id,
        parsed_metric_types,
        start_date=start_date,
        end_date=end_date,
        employee_ids=parsed_employee_ids,
    )
    logger.info(f"Получено {len(employees_data)} сотрудников")
    
    # Генерируем случайные цвета для каждого сотрудника
    colors = [
        "#6366f1", "#8b5cf6", "#a855f7", "#d946ef", "#ec4899",
        "#f43f5e", "#ef4444", "#f97316", "#f59e0b", "#eab308",
        "#84cc16", "#22c55e", "#10b981", "#14b8a6", "#06b6d4",
        "#0ea5e9", "#3b82f6", "#ccc6f1", "#8b5cf6", "#a855f7"
    ]
    
    # Формируем labels (названия метрик)
    labels = [metrics_names[metric_type] for metric_type in parsed_metric_types]
    
    # Формируем datasets (данные сотрудников)
    datasets = []
    for i, employee in enumerate(employees_data):
        employee_name = f"{employee.first_name} {employee.last_name}"
        data = []
        
        for metric_type in parsed_metric_types:
            metric_value = float(getattr(employee, f"avg_{metric_type}") or 0.0)
            data.append(round(metric_value, 2))
        
        dataset = ChartDataset(
            label=employee_name,
            data=data,
            backgroundColor=colors[i % len(colors)]
        )
        datasets.append(dataset)
    
    return EmployeeMetricsChartResponse(
        labels=labels,
        datasets=datasets
    )


# эндпоинт для получения количества диалогов в разрезе названий словарей из поля dictionaries диалога или свойства dictionaries_list
@router.get("/get-dialogs-by-dictionaries", response_model=List[DialogsByDictionariesResponse], description="Получение диалогов по названиям словарей")
async def get_dialogs_by_dictionaries(
    employee_ids: Optional[str] = Query(None, description="Список ID сотрудников через запятую"),
    start_date: Optional[datetime] = Query(None, description="Дата начала фильтра"),
    end_date: Optional[datetime] = Query(None, description="Дата окончания фильтра"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> List[DialogsByDictionariesResponse]:
    """Получение диалогов по названиям словарей"""
    organization_id = current_user.organization_id
    return await dialog_crud.get_dialogs_by_dictionaries(db, organization_id, start_date, end_date, employee_ids)


# @router.get("/get-dialogs-by-type/{conversation_type}", response_model=List[DialogList], description="Получение диалогов по типу разговора")
# async def get_dialogs_by_type(
#     conversation_type: str,
#     current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
#     db: AsyncSession = Depends(get_db)
# ) -> List[DialogList]:
#     """Получение диалогов по типу разговора"""
#     try:
#         conv_type = ConversationType(conversation_type)
#     except ValueError:
#         raise HTTPException(status_code=400, detail="Неверный тип разговора")
    
#     return await dialog_crud.get_by_conversation_type(db, conv_type)


# @router.get("/search-dialogs", response_model=List[DialogList], description="Поиск диалогов по имени файла")
# async def search_dialogs(
#     filename: str = Query(..., description="Часть имени файла для поиска"),
#     current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
#     db: AsyncSession = Depends(get_db)
# ) -> List[DialogList]:
#     """Поиск диалогов по части имени файла"""
#     return await dialog_crud.search_by_filename(db, filename)


# @router.get("/get-recent-dialogs", response_model=List[DialogList], description="Получение недавних диалогов")
# async def get_recent_dialogs(
#     days: int = Query(7, description="Количество дней для поиска"),
#     current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
#     db: AsyncSession = Depends(get_db)
# ) -> List[DialogList]:
#     """Получение диалогов за последние N дней"""
#     return await dialog_crud.get_recent_dialogs(db, days)


# Эндпоинты для работы с AudioData

@router.get("/audio-data/stats", response_model=AudioDataStats, description="Получение статистики по аудиозаписям")
async def get_audio_data_stats(
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
) -> AudioDataStats:
    """Получение статистики по аудиозаписям"""
    try:
        stats = await voca_service.get_audio_data_stats(db)
        return AudioDataStats(**stats)
    except Exception as e:
        logger.error(f"Ошибка при получении статистики аудиозаписей: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при получении статистики: {str(e)}"
        )


# @router.get("/audio-data/unprocessed", response_model=List[AudioDataList], description="Получение необработанных аудиозаписей")
# async def get_unprocessed_audio_data(
#     limit: int = Query(100, description="Максимальное количество записей"),
#     current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
#     db: AsyncSession = Depends(get_db)
# ) -> List[AudioDataList]:
#     """Получение необработанных аудиозаписей"""
#     try:
#         records = await voca_service.get_unprocessed_audio_data(db, limit)
#         return [AudioDataList(**record) for record in records]
#     except Exception as e:
#         logger.error(f"Ошибка при получении необработанных аудиозаписей: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Ошибка при получении необработанных записей: {str(e)}"
#         )


# @router.post("/audio-data/{audio_data_id}/mark-processed", description="Отметить аудиозапись как обработанную")
# async def mark_audio_data_as_processed(
#     audio_data_id: int,
#     current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
#     db: AsyncSession = Depends(get_db)
# ):
#     """Отметить аудиозапись как обработанную"""
#     try:
#         success = await voca_service.mark_audio_data_as_processed(db, audio_data_id)
#         if success:
#             return {"message": f"Запись {audio_data_id} отмечена как обработанная"}
#         else:
#             raise HTTPException(
#                 status_code=404,
#                 detail=f"Запись {audio_data_id} не найдена"
#             )
#     except Exception as e:
#         logger.error(f"Ошибка при отметке записи {audio_data_id} как обработанной: {e}")
#         raise HTTPException(
#             status_code=500,
#             detail=f"Ошибка при отметке записи как обработанной: {str(e)}"
#         )


@router.post("/audio-data/process-previous-day", description="Обработать аудиоданные за предыдущие сутки")
async def process_audio_data_previous_day(
    target_date: Optional[datetime] = Query(None, description="Дата, для которой обрабатываем предыдущие сутки (если не указана, используется текущая дата)"),
    current_user: UserResponse = Security(get_current_user, scopes=['admin', 'operator']),
    db: AsyncSession = Depends(get_db)
):
    """
    Обработать аудиоданные за предыдущие сутки перед транскрибацией и анализом
    
    - Получает необработанные записи из таблицы audio_data за предыдущие сутки
    - Склеивает аудиофайлы для каждого сотрудника в хронологическом порядке
    - Сохраняет склеенные файлы в папку full_speech_data/{employee_id}_{дата}/
    - Отмечает записи как обработанные (is_processed = True)
    - Создает записи в таблице audio_data_for_analysis
    """
    try:
        logger.info(f"Запуск обработки аудиоданных пользователем {current_user.username}")
        
        # Обрабатываем аудиоданные
        results = await audio_processor.process_all_audio_data(db, target_date)
        
        if results:
            processed_count = len(results)
            logger.info(f"Успешно обработано {processed_count} сотрудников")
            
            return {
                "success": True,
                "message": f"Обработано {processed_count} сотрудников",
                "processed_count": processed_count,
                "results": results
            }
        else:
            logger.info("Нет данных для обработки")
            return {
                "success": True,
                "message": "Нет данных для обработки",
                "processed_count": 0,
                "results": {}
            }
            
    except Exception as e:
        logger.error(f"Ошибка при обработке аудиоданных: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ошибка при обработке аудиоданных: {str(e)}"
        )
