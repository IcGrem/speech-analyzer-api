from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base_class import Base


class Analysis(Base):
    """Модель анализа речи"""
    
    title: Mapped[str] = mapped_column(String(255), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=True)
    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(50), default="pending")  # pending, processing, completed, failed
    result: Mapped[dict] = mapped_column(JSON, nullable=True)  # Результат анализа в JSON формате
    