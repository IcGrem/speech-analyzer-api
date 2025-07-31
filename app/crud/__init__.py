"""
CRUDE operations for the database.
"""
from .base import CRUDBase
from .analysis import CRUDAnalysis, analysis_crud

__all__ = ["CRUDBase", "CRUDAnalysis", "analysis_crud"] 