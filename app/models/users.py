from datetime import datetime, timezone
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey, Enum
from app.db.base_class import Base
import enum
import uuid


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    OPERATOR = "operator"


class User(Base):
    __tablename__ = "users"
    
    username: Mapped[str] = mapped_column(unique=True, index=True, nullable=False)
    first_name: Mapped[str] = mapped_column(nullable=True)
    last_name: Mapped[str] = mapped_column(nullable=True)
    middle_name: Mapped[str] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(unique=True, index=True, nullable=True)
    phone: Mapped[str] = mapped_column(unique=True, index=True, nullable=True)
    hashed_password: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False, default=UserRole.OPERATOR)
    is_active: Mapped[bool] = mapped_column(default=True)


class Organization(Base):
    __tablename__ = "organizations"
    
    name: Mapped[str] = mapped_column(nullable=False)
    description: Mapped[str] = mapped_column(nullable=True)
    address: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(nullable=True)
    
    # Связь с сотрудниками
    employees: Mapped[list["Employee"]] = relationship("Employee", back_populates="organization")


class Employee(Base):
    __tablename__ = "employees"
    
    first_name: Mapped[str] = mapped_column(nullable=False)
    last_name: Mapped[str] = mapped_column(nullable=True)
    middle_name: Mapped[str] = mapped_column(nullable=True)
    position: Mapped[str] = mapped_column(nullable=True)
    phone: Mapped[str] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(nullable=True)
    organization_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("organizations.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    
    # Связи
    organization: Mapped["Organization"] = relationship("Organization", back_populates="employees")
