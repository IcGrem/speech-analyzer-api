import asyncio
import json
import random
from datetime import datetime, timedelta, timezone
from typing import List
import uuid

from faker import Faker
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.session import async_session
from app.models.users import Organization, Employee
from app.models.dialogs import Dialog, ConversationType
from app.models.users import UserRole

fake = Faker('ru_RU')


def generate_organization() -> dict:
    """Генерирует данные организации"""
    return {
        "name": fake.company(),
        "description": fake.text(max_nb_chars=200),
        "address": fake.address(),
        "phone": fake.phone_number(),
        "email": fake.company_email()
    }


def generate_employee(organization_id: uuid.UUID) -> dict:
    """Генерирует данные сотрудника"""
    return {
        "employee_id": fake.unique.random_int(min=100000, max=999999),
        "first_name": fake.first_name(),
        "last_name": fake.last_name(),
        "middle_name": fake.middle_name(),
        "position": fake.job(),
        "phone": fake.phone_number(),
        "email": fake.email(),
        "organization_id": organization_id,
        "is_active": True
    }


def generate_conversation() -> str:
    """Генерирует фейковый разговор в JSON формате"""
    messages = []
    speakers = ["Сотрудник", "Клиент"]
    
    for i in range(random.randint(5, 15)):
        speaker = random.choice(speakers)
        message = fake.text(max_nb_chars=100)
        timestamp = fake.date_time_between(start_date='-1h', end_date='now', tzinfo=timezone.utc)
        
        messages.append({
            "speaker": speaker,
            "message": message,
            "timestamp": timestamp.isoformat()
        })
    
    return json.dumps(messages, ensure_ascii=False)


def generate_dialog_metrics() -> dict:
    """Генерирует реалистичные метрики диалога"""
    return {
        "greeting_farewell_score": round(random.uniform(0.1, 5.0), 2),
        "completeness_score": round(random.uniform(0.1, 5.0), 2),
        "tone_score": round(random.uniform(0.1, 5.0), 2),
        "openness_helpfulness_score": round(random.uniform(0.1, 5.0), 2),
        "listening_score": round(random.uniform(0.1, 5.0), 2),
        "empathy_score": round(random.uniform(0.1, 5.0), 2),
        "speech_quality_score": round(random.uniform(0.1, 5.0), 2),
        "response_time_score": round(random.uniform(0.1, 5.0), 2),
        "overall_score": round(random.uniform(0.1, 5.0), 2)
    }


def generate_dialog(employee_id: uuid.UUID, date: datetime) -> dict:
    """Генерирует данные диалога"""
    # Генерируем время начала и окончания записи в пределах дня
    start_time = date.replace(
        hour=random.randint(8, 18),
        minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )
    
    duration_minutes = random.randint(5, 45)
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    metrics = generate_dialog_metrics()
    
    return {
        "employee_id": employee_id,
        "conversation_type": random.choice(list(ConversationType)),
        "conversation": generate_conversation(),
        "filename": f"recording_{start_time.strftime('%Y%m%d_%H%M%S')}_{employee_id}.wav",
        "recording_start_date": start_time,
        "recording_end_date": end_time,
        **metrics
    }


async def seed_data():
    """Основная функция для заполнения базы данных"""
    async with async_session() as session:
        # Создаем организацию
        print("Создаем организацию...")
        org_data = generate_organization()
        organization = Organization(**org_data)
        session.add(organization)
        await session.flush()
        
        # Создаем 10 сотрудников
        print("Создаем сотрудников...")
        employees = []
        for _ in range(10):
            emp_data = generate_employee(organization.id)
            employee = Employee(**emp_data)
            employees.append(employee)
            session.add(employee)
        
        await session.flush()
        
        # Создаем диалоги для каждого сотрудника батчами
        print("Создаем диалоги...")
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        batch_size = 100  # Сохраняем по 100 диалогов за раз
        
        for employee in employees:
            print(f"Создаем диалоги для сотрудника {employee.first_name} {employee.last_name}...")
            
            for day in range(30):
                current_date = start_date + timedelta(days=day)
                
                # 20 диалогов в день
                for _ in range(20):
                    dialog_data = generate_dialog(employee.id, current_date)
                    dialog = Dialog(**dialog_data)
                    session.add(dialog)
                    
                    # Сохраняем батчами
                    if len(session.new) >= batch_size:
                        await session.commit()
                        print(f"Сохранено {batch_size} диалогов...")
        
        # Сохраняем оставшиеся диалоги
        if len(session.new) > 0:
            await session.commit()
            print(f"Сохранено {len(session.new)} оставшихся диалогов...")
        
        print("Данные успешно добавлены!")


if __name__ == "__main__":
    asyncio.run(seed_data()) 