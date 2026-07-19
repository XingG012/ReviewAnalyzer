"""SQLAlchemy 模型 — Alembic 自动发现需要导入所有模型"""

from app.models.base import Base
from app.models.persona import GoldenSample, Persona
from app.models.report import AnalysisReport
from app.models.review import Review, TaggedReview
from app.models.task import Task
from app.models.upload import Upload

__all__ = [
    "Base",
    "Task",
    "Review",
    "TaggedReview",
    "Persona",
    "GoldenSample",
    "AnalysisReport",
    "Upload",
]
