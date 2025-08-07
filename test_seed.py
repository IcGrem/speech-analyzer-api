#!/usr/bin/env python3
"""
Тестовый скрипт для проверки проблемы с timezone
"""

import sys
import os
import asyncio
from datetime import datetime, timezone

# Добавляем корневую директорию в PYTHONPATH
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.db.session import async_session
from app.models.users import Organization, Employee
from app.models.dialogs import Dialog, ConversationType
from faker import Faker

fake = Faker('ru_RU')

async def test_single_dialog():
    """Тестируем создание одного диалога"""
    async with async_session() as session:
        # Создаем организацию
        org = Organization(
            name="Тестовая организация",
            description="Описание",
            address="Адрес",
            phone="+7-999-123-45-67",
            email="test@example.com"
        )
        session.add(org)
        await session.flush()
        
        # Создаем сотрудника
        emp = Employee(
            first_name="Иван",
            last_name="Иванов",
            position="Менеджер",
            organization_id=org.id,
            is_active=True
        )
        session.add(emp)
        await session.flush()
        
        # Создаем один диалог
        dialog = Dialog(
            employee_id=emp.id,
            conversation_type=ConversationType.M2C,
            conversation='[{"speaker": "Сотрудник", "message": "Тест", "timestamp": "2025-08-07T12:00:00+00:00"}]',
            filename="test.wav",
            recording_start_date=datetime.now(timezone.utc),
            recording_end_date=datetime.now(timezone.utc),
            greeting_farewell_score=1.0,
            completeness_score=1.0,
            tone_score=1.0,
            openness_helpfulness_score=1.0,
            listening_score=1.0,
            empathy_score=1.0,
            speech_quality_score=1.0,
            response_time_score=1.0,
            overall_score=1.0
        )
        session.add(dialog)
        
        await session.commit()
        print("Тестовый диалог успешно создан!")

if __name__ == "__main__":
    asyncio.run(test_single_dialog()) 