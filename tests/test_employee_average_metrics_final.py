import pytest
from unittest.mock import AsyncMock, patch
from uuid import uuid4
from datetime import datetime

from app.api.v1.endpoints.dialogs import get_employee_average_metrics
from app.schemas.dialogs import EmployeeMetricsChartResponse


@pytest.mark.asyncio
async def test_get_employee_average_metrics_logic():
    """Тест логики получения средних метрик сотрудников"""
    
    # Мокаем данные сотрудников
    mock_employees_data = [
        type('Employee', (), {
            'id': uuid4(),
            'first_name': 'Федор',
            'last_name': 'Иванов',
            'avg_greeting_farewell_score': 3.2,
            'avg_completeness_score': 2.8,
            'avg_overall_score': 3.0
        })(),
        type('Employee', (), {
            'id': uuid4(),
            'first_name': 'Вася',
            'last_name': 'Пупкин',
            'avg_greeting_farewell_score': 2.2,
            'avg_completeness_score': 2.5,
            'avg_overall_score': 2.7
        })()
    ]
    
    organization_id = uuid4()
    metric_types = "greeting_farewell_score,completeness_score,overall_score"
    
    # Мокаем зависимости
    mock_db = AsyncMock()
    mock_current_user = type('User', (), {
        'username': 'test_user',
        'scopes': ['admin']
    })()
    
    with patch('app.crud.dialogs.dialog_crud.get_employee_average_metrics_by_organization', 
               new_callable=AsyncMock) as mock_crud:
        mock_crud.return_value = mock_employees_data
        
        # Вызываем функцию напрямую
        result = await get_employee_average_metrics(
            organization_id=organization_id,
            metric_types=metric_types,
            start_date=None,
            end_date=None,
            current_user=mock_current_user,
            db=mock_db
        )
    
    # Проверяем результат
    assert isinstance(result, EmployeeMetricsChartResponse)
    assert "labels" in result.model_dump()
    assert "datasets" in result.model_dump()
    
    # Проверяем labels (названия метрик)
    expected_labels = ["Приветствие и прощание", "Полнота ответа", "Итоговая оценка"]
    assert result.labels == expected_labels
    
    # Проверяем datasets (данные сотрудников)
    assert len(result.datasets) == 2
    
    # Проверяем первого сотрудника
    employee1 = result.datasets[0]
    assert employee1.label == "Федор Иванов"
    assert employee1.data == [3.2, 2.8, 3.0]
    assert employee1.backgroundColor is not None
    
    # Проверяем второго сотрудника
    employee2 = result.datasets[1]
    assert employee2.label == "Вася Пупкин"
    assert employee2.data == [2.2, 2.5, 2.7]
    assert employee2.backgroundColor is not None
    
    # Проверяем, что CRUD был вызван с правильными параметрами
    mock_crud.assert_called_once_with(
        mock_db, 
        organization_id, 
        ['greeting_farewell_score', 'completeness_score', 'overall_score'],
        None, 
        None
    )


@pytest.mark.asyncio
async def test_get_employee_average_metrics_with_date_filter():
    """Тест с фильтром по датам"""
    
    organization_id = uuid4()
    metric_types = "greeting_farewell_score,overall_score"
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    mock_employees_data = [
        type('Employee', (), {
            'id': uuid4(),
            'first_name': 'Тест',
            'last_name': 'Сотрудник',
            'avg_greeting_farewell_score': 3.0,
            'avg_overall_score': 3.5
        })()
    ]
    
    mock_db = AsyncMock()
    mock_current_user = type('User', (), {
        'username': 'test_user',
        'scopes': ['admin']
    })()
    
    with patch('app.crud.dialogs.dialog_crud.get_employee_average_metrics_by_organization', 
               new_callable=AsyncMock) as mock_crud:
        mock_crud.return_value = mock_employees_data
        
        result = await get_employee_average_metrics(
            organization_id=organization_id,
            metric_types=metric_types,
            start_date=start_date,
            end_date=end_date,
            current_user=mock_current_user,
            db=mock_db
        )
    
    assert isinstance(result, EmployeeMetricsChartResponse)
    assert len(result.datasets) == 1
    
    # Проверяем, что CRUD был вызван с правильными параметрами дат
    mock_crud.assert_called_once()
    call_args = mock_crud.call_args
    # Проверяем позиционные аргументы
    assert call_args[0][0] == mock_db  # db
    assert call_args[0][1] == organization_id  # organization_id
    assert call_args[0][2] == ['greeting_farewell_score', 'overall_score']  # metric_types
    assert call_args[0][3] == start_date  # start_date
    assert call_args[0][4] == end_date  # end_date


@pytest.mark.asyncio
async def test_get_employee_average_metrics_response_format():
    """Тест формата ответа для фронтенда"""
    
    organization_id = uuid4()
    metric_types = "greeting_farewell_score,completeness_score"
    
    mock_employees_data = [
        type('Employee', (), {
            'id': uuid4(),
            'first_name': 'Иван',
            'last_name': 'Петров',
            'avg_greeting_farewell_score': 4.0,
            'avg_completeness_score': 3.8
        })()
    ]
    
    mock_db = AsyncMock()
    mock_current_user = type('User', (), {
        'username': 'test_user',
        'scopes': ['admin']
    })()
    
    with patch('app.crud.dialogs.dialog_crud.get_employee_average_metrics_by_organization', 
               new_callable=AsyncMock) as mock_crud:
        mock_crud.return_value = mock_employees_data
        
        result = await get_employee_average_metrics(
            organization_id=organization_id,
            metric_types=metric_types,
            start_date=None,
            end_date=None,
            current_user=mock_current_user,
            db=mock_db
        )
    
    # Проверяем формат ответа для фронтенда
    response_dict = result.model_dump()
    
    # Проверяем структуру
    assert "labels" in response_dict
    assert "datasets" in response_dict
    
    # Проверяем labels
    assert response_dict["labels"] == ["Приветствие и прощание", "Полнота ответа"]
    
    # Проверяем datasets
    assert len(response_dict["datasets"]) == 1
    dataset = response_dict["datasets"][0]
    
    assert "label" in dataset
    assert "data" in dataset
    assert "backgroundColor" in dataset
    
    assert dataset["label"] == "Иван Петров"
    assert dataset["data"] == [4.0, 3.8]
    assert isinstance(dataset["backgroundColor"], str)
    assert dataset["backgroundColor"].startswith("#")
