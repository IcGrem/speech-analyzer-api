import enum
from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Enum, String, Float
from uuid import UUID
from typing import Any

from app.models.users import Employee
from app.db.base_class import Base


class ConversationType(str, enum.Enum):
    M2M = "m2m"  # manager to manager
    M2C = "m2c"  # manager to customer
    UNKNOWN = "unknown"


class Dialog(Base):
    __tablename__ = "dialogs"
    
    employee_id: Mapped[UUID] = mapped_column(ForeignKey("employees.id"), nullable=False)
    conversation_type: Mapped[ConversationType] = mapped_column(Enum(ConversationType), nullable=False, default=ConversationType.UNKNOWN)
    conversation: Mapped[str] = mapped_column(String, nullable=False)  # JSON поле для хранения разговора
    filename: Mapped[str] = mapped_column(nullable=False)  # Наименование файла
    recording_start_date: Mapped[datetime] = mapped_column(nullable=False)  # Дата начала записи
    recording_end_date: Mapped[datetime] = mapped_column(nullable=False)  # Дата окончания записи
    
    # Метрики диалога
    greeting_farewell_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Приветствие и прощание
    completeness_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Полнота ответа
    tone_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Тон общения
    openness_helpfulness_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Открытость и готовность помочь
    listening_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Умение слушать
    empathy_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Эмпатия
    speech_quality_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Грамотная речь
    response_time_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Время ответа
    overall_score: Mapped[float] = mapped_column(Float, nullable=True, default=0.0)  # Итоговая оценка
    
    # Связь с сотрудником
    employee: Mapped["Employee"] = relationship("Employee", backref="dialogs")
