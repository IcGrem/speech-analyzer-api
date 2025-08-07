from typing import Any
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime, timezone
import uuid
from sqlalchemy import text, DateTime
from sqlalchemy.dialects.postgresql import UUID


class Base(DeclarativeBase):
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        # server_default=text("gen_random_uuid()"),
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.now(timezone.utc), onupdate=datetime.now(timezone.utc)
    )

    @declared_attr.directive
    def __tablename__(cls) -> str:
        """Автоматически создает имя таблицы на основе имени класса."""
        return cls.__name__.lower()

    def dict(self) -> dict[str, Any]:
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
