import asyncio
import json
import random
import math
from datetime import datetime, timedelta, timezone
import uuid

from faker import Faker

from app.db.session import async_session
from app.models.users import Organization, Employee
from app.models.dialogs import Dialog, ConversationType

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
    
    for _ in range(random.randint(5, 15)):
        speaker = random.choice(speakers)
        message = fake.text(max_nb_chars=100)
        timestamp = fake.date_time_between(start_date='-1h', end_date='now', tzinfo=timezone.utc)
        
        messages.append({
            "speaker": speaker,
            "message": message,
            "timestamp": timestamp.isoformat()
        })
    
    return json.dumps(messages, ensure_ascii=False)


METRIC_NAMES = [
    "greeting_farewell_score",
    "completeness_score",
    "tone_score",
    "openness_helpfulness_score",
    "listening_score",
    "empathy_score",
    "speech_quality_score",
    "response_time_score",
]

DEFAULT_WEIGHTS = {
    "greeting_farewell_score": 0.08,
    "completeness_score": 0.14,
    "tone_score": 0.12,
    "openness_helpfulness_score": 0.14,
    "listening_score": 0.18,
    "empathy_score": 0.18,
    "speech_quality_score": 0.10,
    "response_time_score": 0.06,
}


def clamp_0_5(x: float) -> float:
    return max(0.1, min(5.0, x))


def build_employee_profiles(employees: list[Employee]) -> tuple[dict, dict]:
    """Создает профиль и начальное состояние по каждому сотруднику."""
    profiles: dict[uuid.UUID, dict] = {}
    states: dict[uuid.UUID, dict] = {}
    for e in employees:
        base_quality = random.uniform(1.5, 4.3)
        profile = {"baseline": {}, "phi": {}, "sigma": {}, "weights": DEFAULT_WEIGHTS}
        state = {}
        for m in METRIC_NAMES:
            baseline = clamp_0_5(base_quality + random.gauss(0.0, 0.4))
            phi = random.uniform(0.7, 0.95)
            sigma = random.uniform(0.06, 0.22)
            profile["baseline"][m] = baseline
            profile["phi"][m] = phi
            profile["sigma"][m] = sigma
            state[m] = baseline
        profiles[e.id] = profile
        states[e.id] = state
    return profiles, states


def generate_dialog_metrics(profile: dict, state: dict, current_date: datetime, day_index: int) -> dict:
    """AR(1) по каждой метрике + сезонность по дням недели + небольшой тренд."""
    weekday = current_date.weekday()
    season = 0.12 * math.sin(2 * math.pi * (weekday / 7.0))
    trend = min(0.5, 0.01 * (day_index / 30))

    out = {}
    for m in METRIC_NAMES:
        baseline = profile["baseline"][m] + season + trend
        phi = profile["phi"][m]
        sigma = profile["sigma"][m]
        prev = state.get(m, baseline)
        value = phi * prev + (1 - phi) * baseline + random.gauss(0.0, sigma)
        value = clamp_0_5(value)
        state[m] = value
        out[m] = round(value, 2)

    weights = profile["weights"]
    overall = sum(out[m] * weights[m] for m in METRIC_NAMES) + random.gauss(0.0, 0.05)
    out["overall_score"] = round(clamp_0_5(overall), 2)
    return out


def generate_dialog(employee_id: uuid.UUID, date: datetime, profile: dict, state: dict, day_index: int) -> dict:
    """Генерирует данные диалога"""
    start_time = date.replace(
        hour=random.randint(8, 18),
        minute=random.randint(0, 59),
        second=random.randint(0, 59)
    )
    
    duration_minutes = random.randint(5, 45)
    end_time = start_time + timedelta(minutes=duration_minutes)
    
    metrics = generate_dialog_metrics(profile, state, date, day_index)
    
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
        print("Создаем организацию...")
        org_data = generate_organization()
        organization = Organization(**org_data)
        session.add(organization)
        await session.flush()
        
        print("Создаем сотрудников...")
        employees: list[Employee] = []
        for _ in range(10):
            emp_data = generate_employee(organization.id)
            employee = Employee(**emp_data)
            employees.append(employee)
            session.add(employee)
        
        await session.flush()
        
        # Профили сотрудников для стабильных средних и автокорреляции
        employee_profiles, employee_states = build_employee_profiles(employees)
        
        print("Создаем диалоги...")
        start_date = datetime.now(timezone.utc) - timedelta(days=30)
        batch_size = 100
        pending = 0
        total_saved = 0
        
        for employee in employees:
            print(f"Создаем диалоги для сотрудника {employee.first_name} {employee.last_name}...")
            profile = employee_profiles[employee.id]
            state = employee_states[employee.id]
            
            for day in range(30):
                current_date = start_date + timedelta(days=day)
                
                for _ in range(20):
                    dialog_data = generate_dialog(employee.id, current_date, profile, state, day)
                    dialog = Dialog(**dialog_data)
                    session.add(dialog)
                    pending += 1
                    
                    if pending >= batch_size:
                        await session.commit()
                        total_saved += pending
                        print(f"Сохранено {pending} диалогов...")
                        pending = 0
        
        if pending > 0:
            await session.commit()
            total_saved += pending
            print(f"Сохранено {pending} оставшихся диалогов...")
        
        print(f"Данные успешно добавлены! Всего сохранено диалогов: {total_saved}")


if __name__ == "__main__":
    asyncio.run(seed_data())