"""
Base for importing all models.
"""

from app.db.base_class import Base
from app.models.analysis import Analysis
from app.models.dialogs import Dialog
from app.models.users import User, Employee, Organization

__all__ = [
    "Base",
    "Analysis",
    "Dialog",
    "User",
    "Employee",
    "Organization",
]

