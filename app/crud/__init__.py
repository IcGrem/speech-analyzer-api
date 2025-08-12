"""
CRUDE operations for the database.
"""
from .base import CRUDBase
from .analysis import CRUDAnalysis, analysis_crud
from .audio_data import CRUDAudioData, audio_data_crud

__all__ = ["CRUDBase", "CRUDAnalysis", "analysis_crud", "CRUDAudioData", "audio_data_crud"] 